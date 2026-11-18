#!/usr/bin/env python3
"""Sparring partners for local benchmarking: Stockfish on a last-seen guess of the board.

FOW_STYLE (or --style) picks plain, hunter, greedy or random. Never uploaded.
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from pathlib import Path

# Make `fow` importable from the flat packaged layout (fow/ next to bot.py)
# or from the repo layout (bots/<name>/bot.py with fow/ at the repo root).
_HERE = Path(__file__).resolve().parent
for _root in (_HERE, *_HERE.parents[1:2]):
    if (_root / "fow").is_dir() and str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import chess  # noqa: E402
import chess.engine  # noqa: E402

from fow.protocol import Agent, log, run  # noqa: E402
from uniform_random import ObservationTracker, candidates  # noqa: E402  (starter kit)

STYLES = ("plain", "hunter", "greedy", "random")
DEFAULT_STOCKFISH = _HERE.parents[1] / "bots" / "obscuro" / "stockfish" / "src" / "stockfish"
PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9,
                chess.KING: 100}
START_COUNTS = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1,
                chess.KING: 1}
DEPTH = 8
MOVE_TIME = 0.3
MAX_MULTIPV = 30
UNSCORED = -10_000.0  # a candidate the engine would not search (leaves our king en prise)
MAX_RESTARTS = 2


class LastSeenBoard:
    """Guess of the full board: what we see now, plus where unseen enemy pieces last were."""

    def __init__(self, side: chess.Color):
        self.side = side
        self.enemy = {sq: p for sq, p in chess.Board().piece_map().items() if p.color != side}
        self.king_last = chess.E8 if side == chess.WHITE else chess.E1
        self.obs = "?" * 64
        self.unseen = 0
        self.moved_from: set[chess.Square] = set()

    def moved(self, board: chess.Board, move: chess.Move) -> None:
        """Our own move: these squares empty without an enemy capture."""
        self.moved_from = {move.from_square}
        if board.is_castling(move):
            rank = chess.square_rank(move.from_square)
            self.moved_from.add(chess.square(0 if move.to_square < move.from_square else 7, rank))

    def update(self, obs: str) -> None:
        previous = self.obs
        own = lambda char: char not in "?-" and char.isupper() == (self.side == chess.WHITE)  # noqa: E731
        appeared = []
        for sq, char in enumerate(obs):
            if char == "?":
                continue
            was = self.enemy.pop(sq, None)
            if char != "-" and char.isupper() != (self.side == chess.WHITE):
                piece = chess.Piece.from_symbol(char)
                self.enemy[sq] = piece
                if was != piece:
                    appeared.append(sq)
        # A pawn's capture squares are only shown when occupied, so an unseen one is empty.
        pawn, step = ("P", 8) if self.side == chess.WHITE else ("p", -8)
        for sq, char in enumerate(obs):
            if char == pawn:
                for diagonal in (sq + step - 1, sq + step + 1):
                    if 0 <= diagonal < 64 and chess.square_distance(sq, diagonal) == 1 and obs[diagonal] == "?":
                        self.enemy.pop(diagonal, None)
        self.obs = obs
        self.unseen = obs.count("?")
        # A piece that turned up where we did not expect it came from somewhere: drop the
        # unseen guess of the same type nearest to it while the type is over its count.
        for sq in appeared:
            piece = self.enemy[sq]
            seen = [s for s, p in self.enemy.items() if p == piece]
            while len(seen) > START_COUNTS[piece.piece_type] or piece.piece_type == chess.KING:
                unseen = [s for s in seen if obs[s] == "?"]
                if not unseen:
                    break
                gone = min(unseen, key=lambda s: chess.square_distance(s, sq))
                del self.enemy[gone]
                seen.remove(gone)
        # One of our pieces vanished from a square we no longer see: an enemy piece took it
        # and stands there. Bring the likeliest unseen guess (an attacker, else the nearest).
        for sq in range(64):
            if own(previous[sq]) and obs[sq] == "?" and sq not in self.moved_from:
                self._relocate(previous, sq)
        self.moved_from = set()
        for sq, piece in self.enemy.items():
            if piece.piece_type == chess.KING:
                self.king_last = sq

    def _relocate(self, previous: str, target: chess.Square) -> None:
        unseen = [sq for sq in self.enemy if self.obs[sq] == "?" and sq != target]
        if not unseen:
            return
        board = chess.Board(None)
        for sq, char in enumerate(previous):
            if char not in "?-":
                board.set_piece_at(sq, chess.Piece.from_symbol(char))
        for sq, piece in self.enemy.items():
            if board.piece_at(sq) is None:
                board.set_piece_at(sq, piece)
        attackers = [sq for sq in unseen if sq in board.attackers(not self.side, target)]
        source = min(attackers or unseen, key=lambda sq: chess.square_distance(sq, target))
        self.enemy[target] = self.enemy.pop(source)

    def board(self, visible: chess.Board, rights: int) -> chess.Board:
        """A full python-chess board for the engine; ``visible`` is the tracker's board."""
        board = chess.Board(None)
        for sq, piece in visible.piece_map().items():
            board.set_piece_at(sq, piece)
        for sq, piece in self.enemy.items():
            if board.piece_at(sq) is None:
                board.set_piece_at(sq, piece)
        if not board.pieces(chess.KING, not self.side):
            board.set_piece_at(self._king_square(board), chess.Piece(chess.KING, not self.side))
        board.turn = self.side
        board.ep_square = visible.ep_square
        enemy_rank = chess.BB_RANK_8 if self.side == chess.WHITE else chess.BB_RANK_1
        board.castling_rights = rights | (chess.BB_CORNERS & enemy_rank)
        board.castling_rights = board.clean_castling_rights()
        return board

    def _king_square(self, board: chess.Board) -> chess.Square:
        """Nearest empty square to the king's last position: unseen and unattacked if possible."""
        free = [sq for sq in chess.SQUARES if board.piece_at(sq) is None]
        return min(free, key=lambda sq: (self.obs[sq] != "?", board.is_attacked_by(self.side, sq),
                                         chess.square_distance(sq, self.king_last)))

    def fallback(self, visible: chess.Board, rights: int) -> chess.Board:
        """Known pieces only, plus the enemy king."""
        board = chess.Board(None)
        for sq, piece in visible.piece_map().items():
            board.set_piece_at(sq, piece)
        if not board.pieces(chess.KING, not self.side):
            board.set_piece_at(self._king_square(board), chess.Piece(chess.KING, not self.side))
        board.turn = self.side
        board.ep_square = visible.ep_square
        board.castling_rights = rights
        return board


def engine_accepts(board: chess.Board) -> bool:
    """Stockfish exits on positions failing these checks."""
    if board.pawns & (chess.BB_RANK_1 | chess.BB_RANK_8):
        return False
    for color in chess.COLORS:
        own = board.occupied_co[color]
        if chess.popcount(board.kings & own) != 1:
            return False
        pawns = chess.popcount(board.pawns & own)
        promoted = (max(chess.popcount(board.knights & own) - 2, 0)
                    + max(chess.popcount(board.bishops & own) - 2, 0)
                    + max(chess.popcount(board.rooks & own) - 2, 0)
                    + max(chess.popcount(board.queens & own) - 1, 0))
        if pawns > 8 or promoted > 8 - pawns:
            return False
    return not board.is_attacked_by(board.turn, board.king(not board.turn))


def aims_at_king(board: chess.Board, move: chess.Move, king: chess.Square) -> bool:
    """A slider move landing on an open line with the enemy king square."""
    piece = board.piece_at(move.from_square)
    if piece is None or piece.piece_type not in (chess.ROOK, chess.BISHOP, chess.QUEEN):
        return False
    to = move.to_square
    same_line = chess.square_file(to) == chess.square_file(king) or chess.square_rank(to) == chess.square_rank(king)
    same_diag = abs(chess.square_file(to) - chess.square_file(king)) == abs(chess.square_rank(to) - chess.square_rank(king))
    if piece.piece_type == chess.ROOK and not same_line:
        return False
    if piece.piece_type == chess.BISHOP and not same_diag:
        return False
    if piece.piece_type == chess.QUEEN and not (same_line or same_diag):
        return False
    occupied = (board.occupied & ~chess.BB_SQUARES[move.from_square]) | chess.BB_SQUARES[to]
    return to != king and not (chess.between(to, king) & occupied)


class SparringAgent(Agent):
    def __init__(self, style: str, stockfish: str, seed: int | None = None):
        self.style = style
        self.stockfish = stockfish
        self.rng = random.Random(seed)
        self.tracker: ObservationTracker | None = None
        self.guess: LastSeenBoard | None = None
        self.engine: chess.engine.SimpleEngine | None = None
        self.restarts = 0

    def reset(self, color: bool, base: float, inc: float) -> None:
        self.tracker = ObservationTracker(color)
        self.guess = LastSeenBoard(color)
        log(f"sparring: style {self.style}, playing {'white' if color else 'black'} at {base:g}+{inc:g}")
        if self.style != "random":
            self._start_engine()

    def _start_engine(self) -> bool:
        try:
            # Its own process group: SIGSTOP/SIGCONT on ours would otherwise make asyncio's
            # child watcher block in waitpid on macOS, and the first analyse never returns.
            # The engine only ever works inside our turn, so it idles while we are paused.
            self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish, timeout=10, setpgrp=True)
            options = {name: value for name, value in (("Threads", 1), ("Hash", 16))
                       if name in self.engine.options}
            if options:
                self.engine.configure(options)
            log(f"sparring: engine ready ({self.engine.id.get('name', '?')})")
            return True
        except (OSError, chess.engine.EngineError, TimeoutError) as error:
            log(f"sparring: no engine at {self.stockfish}: {error}")
            self.engine = None
            return False

    def _engine_lost(self, why: str) -> None:
        log(f"sparring: engine lost ({why})")
        try:
            if self.engine is not None:
                self.engine.close()
        except Exception:
            pass
        self.engine = None
        if self.restarts < MAX_RESTARTS:
            self.restarts += 1
            self._start_engine()

    def close(self) -> None:
        """Quit the engine so the process can exit once stdin closes."""
        if self.engine is not None:
            try:
                self.engine.close()
            except Exception:
                pass
            self.engine = None

    def observe(self, obs: str) -> None:
        self.tracker.observe(obs)
        self.guess.update(obs)

    def act(self, remaining_time: float) -> str | None:
        started = time.monotonic()
        tracker = self.tracker
        visible, moves = candidates(tracker.current, tracker.side, tracker.rights, tracker.previous)
        if not moves:
            return None
        move, score, note = self._choose(visible, moves, remaining_time)
        tracker.record_move(move)
        self.guess.moved(visible, move)
        log(f"sparring[{self.style}]: {move.uci()} score={score:+.0f} unseen={self.guess.unseen}"
            f" {note} ({time.monotonic() - started:.2f}s)")
        return move.uci()

    def _choose(self, visible: chess.Board, moves: list[chess.Move], remaining: float):
        if self.style == "random":
            return self.rng.choice(moves), 0.0, "random"
        board = self.guess.board(visible, self.tracker.rights)
        king = board.king(not self.tracker.side)
        for move in moves:
            if move.to_square == king:
                return move, math.inf, "takes the king"
        note = "guess"
        if not engine_accepts(board):
            board = self.guess.fallback(visible, self.tracker.rights)
            note = "fallback board"
        scores = self._engine_scores(board, moves, remaining) if engine_accepts(board) else None
        if scores is None:
            scores = {move: 0.0 for move in moves}
            note += ", no engine"
        best, best_score = None, -math.inf
        for move in moves:
            value = scores.get(move, UNSCORED) + self._bonus(board, move, king) + self.rng.random()
            if value > best_score:
                best, best_score = move, value
        return best, best_score, note

    def _engine_scores(self, board: chess.Board, moves: list[chess.Move], remaining: float):
        if self.engine is None or remaining < 1.0:
            return None
        budget = MOVE_TIME if remaining > 10 else max(0.02, remaining / 60)
        limit = chess.engine.Limit(depth=DEPTH, time=budget)
        try:
            infos = self.engine.analyse(board, limit, multipv=min(len(moves), MAX_MULTIPV), root_moves=moves)
        except (chess.engine.EngineTerminatedError, chess.engine.EngineError, TimeoutError) as error:
            self._engine_lost(str(error)[:80])
            return None
        scores: dict[chess.Move, float] = {}
        for info in infos:
            pv, score = info.get("pv"), info.get("score")
            if pv and score is not None:
                scores[pv[0]] = score.pov(self.tracker.side).score(mate_score=30_000)
        # Moves the engine left out were illegal in its eyes (our king stays en prise),
        # unless MultiPV simply ran out: then they are merely worse than the ones ranked.
        floor = min(scores.values(), default=0.0) - 100 if len(scores) >= MAX_MULTIPV else UNSCORED
        for move in moves:
            scores.setdefault(move, floor)
        return scores

    def _bonus(self, board: chess.Board, move: chess.Move, king: chess.Square) -> float:
        if self.style == "plain":
            return 0.0
        captured = board.piece_at(move.to_square)
        if self.style == "greedy":
            bonus = 100 * PIECE_VALUES[captured.piece_type] if captured else 0
            if board.is_en_passant(move):
                bonus += 100
            return bonus + (300 if move.promotion else 0)
        bonus = 40 if board.is_capture(move) else 0
        if aims_at_king(board, move, king):
            bonus += 60
        board.push(move)
        try:
            if board.is_attacked_by(self.tracker.side, king):
                bonus += 150
        finally:
            board.pop()
        return bonus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--style", choices=STYLES, default=os.environ.get("FOW_STYLE", "plain"))
    parser.add_argument("--stockfish", default=os.environ.get("FOW_STOCKFISH", str(DEFAULT_STOCKFISH)))
    args = parser.parse_args()
    agent = SparringAgent(args.style, args.stockfish, args.seed)
    try:
        run(agent)
    finally:
        agent.close()


if __name__ == "__main__":
    main()
