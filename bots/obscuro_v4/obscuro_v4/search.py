"""One move of search: sample roots, build the subgame, solve it, pick a move."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

import chess
import numpy as np

from .solver import Depth2Solver
from .subgame import SubgameBuilder

BUILD_SHARE = 0.8  # the depth-2 solve converges (gap ~0) in a few hundred iterations
MAX_ROOTS = 200
MIN_ITERATIONS = 20
AHEAD_VALUE = 0.1      # above this we are winning (about half a pawn) and a draw is a bad result
REPEAT_PENALTY = 0.05  # value given up per earlier time our pieces stood where a move puts them
DRAW_SHARE = 0.5       # of our lead, at least, given up by a move that may make it the third time


def move_budget(remaining: float, increment: float) -> float:
    """Seconds to spend on this move: a slice of the bank plus most of the increment."""
    return min(remaining / 30 + 0.8 * increment, remaining / 5)


@dataclass(frozen=True)
class SearchResult:
    move: chess.Move
    value: float
    nash_gap: float
    roots: int
    iterations: int
    repeat_avoided: bool = False


def own_placement(view: str, side: chess.Color, move: chess.Move | None = None) -> str:
    """Where our pieces stand in the observation ``view``, after ``move`` if one is given.

    The referee calls a draw when a position occurs for the third time. We cannot see the
    whole position, but it can only be the same as an earlier one if our own pieces stand
    where they stood then, and those we always know. So this is what the bot counts.
    """
    ours = [c if c not in "?-" and c.isupper() == bool(side) else "-" for c in view]
    if move is not None:
        piece = ours[move.from_square]
        ours[move.from_square] = "-"
        if move.promotion:
            symbol = chess.piece_symbol(move.promotion)
            piece = symbol.upper() if side else symbol
        if piece in "Kk" and abs(chess.square_file(move.to_square) - chess.square_file(move.from_square)) == 2:
            rank, h_side = chess.square_rank(move.from_square), move.to_square > move.from_square
            rook = chess.square(7 if h_side else 0, rank)  # castling: the rook goes too
            ours[chess.square(5 if h_side else 3, rank)], ours[rook] = ours[rook], "-"
        ours[move.to_square] = piece
    return "".join(ours)


def choose_action(strategy: np.ndarray, action_values: np.ndarray, value: float,
                  repeat_counts: np.ndarray | None) -> int:
    """The top action of ``strategy``, unless that may repeat a position while winning.

    ``repeat_counts[a]`` is how often our pieces have already stood where move ``a`` puts
    them (see own_placement); that the same move was played before does not matter, the
    same squares can be reached by another. The first time back costs the move
    REPEAT_PENALTY. The second time back may be the position's third occurrence, a draw
    whatever we are ahead by, so it costs DRAW_SHARE of that lead (and no less than two
    penalties). The best move after these discounts is played. When we are not ahead,
    nothing changes: a draw is then no worse than what we have.
    """
    best = int(np.argmax(strategy))
    if repeat_counts is None or value <= AHEAD_VALUE or repeat_counts[best] == 0:
        return best
    penalty = REPEAT_PENALTY * repeat_counts
    penalty = np.where(repeat_counts >= 2, np.maximum(penalty, DRAW_SHARE * value), penalty)
    return int(np.argmax(action_values - penalty))


def search(states: list[chess.Board], our_moves: list[chess.Move], side: chess.Color,
           budget: float, rng: random.Random,
           repeat_counts: list[int] | None = None) -> SearchResult | None:
    """Top action of the last PCFR+ iterate, or None if no state admits all our moves.

    ``repeat_counts`` (one per move, optional) enables repetition avoidance; see choose_action.
    """
    start = time.monotonic()
    builder = SubgameBuilder(our_moves, side)
    for root in rng.sample(states, len(states)):
        if builder.n_roots >= MAX_ROOTS or time.monotonic() - start > BUILD_SHARE * budget:
            break
        builder.add_root(root)
    if builder.n_roots == 0:
        return None

    solver = Depth2Solver(builder.build())
    while solver.iterations < MIN_ITERATIONS or time.monotonic() - start < budget:
        solver.iterate()

    top = int(np.argmax(solver.ours.strategy))
    counts = None if repeat_counts is None else np.asarray(repeat_counts, dtype=float)
    best = choose_action(solver.ours.strategy, solver.our_action_values(), solver.value, counts)
    return SearchResult(our_moves[best], solver.value, solver.nash_gap(),
                        builder.n_roots, solver.iterations, repeat_avoided=best != top)
