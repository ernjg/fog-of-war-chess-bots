"""How likely each of the opponent's moves is, for weighting the belief.

The belief holds positions; which of them are likely depends on the moves that lead to
them. Obscuro takes that from the opponent strategy its search computed on the previous
move: positions that good play leads to count for more, mixed half and half with equal
odds (appendix C.3 of the paper). This is the same idea without the search tree. Stockfish
scores every move of the opponent's one ply deep, the scores are turned into odds, and
those are mixed with equal odds so that no move is ever ruled out.

It is a model of good play, not of any particular opponent, and it judges the moves as
if the opponent saw the whole board (as Obscuro does for positions it has just sampled).
On 1,427 moves that arena opponents played against us it made the move played about twice
as likely as equal odds do; the two numbers below were chosen on those moves.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence

import chess

from .engine import EnginePool, Job
from .rules import side_to_move_wins
from .stockfish_search import engine_accepts, engine_fen

POLICY_DEPTH = 1            # deeper searches did not predict the moves any better
POLICY_TEMPERATURE = 0.06   # on the value scale of engine.cp_value: 0.06 is about a third of a pawn
POLICY_SHARE = 0.8          # of the probability, the part that follows Stockfish; the rest is equal odds
POLICY_SECONDS = 0.5        # at most, per opponent move, for asking the engines
KING_MISS = 0.02            # chance that an opponent who could take our king did not
# Fog of War favours moves that ordinary chess rates as ordinary: a check from a square we
# cannot see, or a capture, is how kings are lost here. Odds of such moves are multiplied
# by these before mixing (1.0 = off). Measured in games, not chosen from theory.
CHECK_BOOST = 1.0
CAPTURE_BOOST = 1.0
LOSS = -1.0                 # value of a move Stockfish does not list: it gives up the king

OTHER = ""                  # key, in a table of odds, for every move the table does not name

# What the belief asks for: positions with the opponent to move and the number of moves it
# has in each; for each position a table from move (UCI) to probability, with the key
# OTHER for all moves not in it, or None for "no idea" (the belief then uses equal odds).
Policy = Callable[[Sequence[chess.Board], Sequence[int]], list[dict[str, float] | None]]


def move_odds(values: dict[str, float], n_moves: int, temperature: float = POLICY_TEMPERATURE,
              share: float = POLICY_SHARE, boost: dict[str, float] | None = None) -> dict[str, float]:
    """Probabilities for the moves in ``values`` (Stockfish's value of each for the side
    to move), and under OTHER for each of the ``n_moves - len(values)`` moves it left out,
    which are the ones that lose the king at once.

    A move's probability is ``share`` times its softmax weight plus an equal part of the
    rest, so the table sums to 1 over all ``n_moves`` moves.
    """
    n_moves = max(n_moves, len(values), 1)
    top = max(values.values(), default=LOSS)
    other = math.exp((LOSS - top) / temperature)
    weight = {move: math.exp((value - top) / temperature) * (boost or {}).get(move, 1.0)
              for move, value in values.items()}
    total = sum(weight.values()) + (n_moves - len(values)) * other
    even = (1.0 - share) / n_moves
    odds = {move: share * w / total + even for move, w in weight.items()}
    odds[OTHER] = share * other / total + even
    return odds


def _gives_check_or_captures(board: chess.Board, move: chess.Move) -> tuple[bool, bool]:
    captures = board.is_capture(move)
    board.push(move)
    try:
        king = board.king(board.turn)
        check = king is not None and board.is_attacked_by(not board.turn, king)
    finally:
        board.pop()
    return check, captures


class OpponentPolicy:
    """Asks the engines. Whatever goes wrong, a position simply gets no table."""

    def __init__(self, pool: EnginePool, seconds: float = POLICY_SECONDS,
                 check_boost: float = CHECK_BOOST, capture_boost: float = CAPTURE_BOOST):
        self.pool = pool
        self.seconds = seconds
        self.check_boost = check_boost
        self.capture_boost = capture_boost
        self.asked = 0      # positions sent to the engines so far, for the log
        self.answered = 0

    def _boosts(self, board: chess.Board, values: dict[str, float]) -> dict[str, float] | None:
        if self.check_boost == 1.0 and self.capture_boost == 1.0:
            return None
        boosts = {}
        for uci in values:
            move = chess.Move.from_uci(uci)
            check, captures = _gives_check_or_captures(board, move)
            factor = (self.check_boost if check else 1.0) * (self.capture_boost if captures else 1.0)
            if factor != 1.0:
                boosts[uci] = factor
        return boosts or None

    def __call__(self, boards: Sequence[chess.Board], move_counts: Sequence[int]
                 ) -> list[dict[str, float] | None]:
        tables: list[dict[str, float] | None] = [None] * len(boards)
        jobs, owners = [], []
        for index, (board, n_moves) in enumerate(zip(boards, move_counts, strict=True)):
            if side_to_move_wins(board):
                # It could have taken our king and the game went on: it almost never
                # misses that, so whatever it played instead from here is very unlikely.
                tables[index] = {OTHER: KING_MISS / max(n_moves, 1)}
            elif engine_accepts(board):
                jobs.append(Job(engine_fen(board), POLICY_DEPTH))
                owners.append(index)
        if not jobs or self.pool.ready_count() == 0:
            return tables
        self.asked += len(jobs)
        # One-ply searches take a fraction of a millisecond, so none is given a slice of
        # its own: each runs to its end, until the time for all of them is up.
        results = self.pool.run(jobs, time.monotonic() + self.seconds, self.seconds, self.seconds)
        for index, result in zip(owners, results, strict=True):
            if result is None or result.no_moves:
                continue
            depth = result.complete_depth(list(result.scores))
            if depth is None:
                continue
            values = {move: found[depth] for move, found in result.scores.items()}
            tables[index] = move_odds(values, move_counts[index], boost=self._boosts(boards[index], values))
            self.answered += 1
        return tables
