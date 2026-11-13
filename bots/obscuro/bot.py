#!/usr/bin/env python3
"""Reduced Obscuro: belief set + depth-2 imperfect-information subgame + PCFR+."""
from __future__ import annotations

import argparse
import random
from collections import Counter
import sys
import time
import traceback
from pathlib import Path

# Make `fow` importable from the flat packaged layout (fow/ next to bot.py)
# or from the repo layout (bots/<name>/bot.py with fow/ at the repo root).
_HERE = Path(__file__).resolve().parent
for _root in (_HERE, *_HERE.parents[1:2]):
    if (_root / "fow").is_dir() and str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import chess  # noqa: E402

from fow.obscuro.belief import Belief, project  # noqa: E402
from fow.obscuro.search import move_budget, search  # noqa: E402
from fow.protocol import Agent, log, run  # noqa: E402
from uniform_random import ObservationTracker, candidates  # noqa: E402  (starter kit)

MIN_SEARCH_SECONDS = 0.1  # below this the search cannot build a root; play the fallback move
FALLBACK_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                   chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


class ObscuroAgent(Agent):
    def __init__(self, seed: int | None, max_states: int, move_time: float | None):
        self.rng = random.Random(seed)
        self.max_states = max_states
        self.move_time = move_time

    def reset(self, color: bool, base: float, inc: float) -> None:
        self.side = color
        self.increment = inc
        self.tracker = ObservationTracker(color)
        self.belief = Belief(color, self.max_states, self.rng)
        self.last_move: chess.Move | None = None
        self.plies = 0               # observations received = plies played so far + 1
        self.observe_seconds = 0.0   # belief-update time this turn; it runs on our clock
        self.belief_ok = True
        self.fallbacks = 0
        self.played: Counter[tuple[str, str]] = Counter()  # (observation, move) pairs we played
        log(f"obscuro: playing {'white' if color else 'black'} at {base:g}+{inc:g}")

    def observe(self, obs: str) -> None:
        started = time.monotonic()
        self.tracker.observe(obs)
        to_move = chess.WHITE if self.plies % 2 == 0 else chess.BLACK
        self.plies += 1
        own_move, self.last_move = self.last_move, None
        try:
            if not self.belief_ok:
                raise RuntimeError("belief was unusable; rebuilding from the observation")
            self.belief.observe(obs, own_move=own_move)
        except Exception:
            self._rebuild_belief(obs, to_move)
        self.observe_seconds += time.monotonic() - started

    def _rebuild_belief(self, obs: str, to_move: chess.Color) -> None:
        """The exact update failed: project the old states onto what we see now.

        The result agrees with the observation but is no longer exact. If even
        this fails, the belief is marked unusable and act() plays fallback moves
        until a later rebuild succeeds.
        """
        log("obscuro: belief update failed, rebuilding from the observation")
        traceback.print_exc(file=sys.stderr)
        try:
            rebuilt = Belief._unique(project(board, obs, self.side, to_move)
                                     for board in self.belief.states)
            if not rebuilt:
                raise RuntimeError("no states to rebuild from")
            if len(rebuilt) > self.max_states:
                rebuilt = self.rng.sample(rebuilt, self.max_states)
            self.belief.states = rebuilt
            self.belief._started = True
            self.belief.repairs += 1
            self.belief_ok = True
        except Exception:
            log("obscuro: belief rebuild failed, playing fallback moves until it recovers")
            traceback.print_exc(file=sys.stderr)
            self.belief_ok = False

    def act(self, remaining_time: float) -> str | None:
        spent, self.observe_seconds = self.observe_seconds, 0.0
        moves = self._legal_moves()
        if not moves:
            return None
        if len(moves) == 1:
            move = moves[0]
        else:
            try:
                move = self._search(moves, remaining_time, spent)
            except Exception:
                log("obscuro: search failed, playing a fallback move")
                traceback.print_exc(file=sys.stderr)
                move = self._fallback_move(moves)
        self.played[self.tracker.current, move.uci()] += 1
        self.tracker.record_move(move)
        self.last_move = move
        return move.uci()

    def _legal_moves(self) -> list[chess.Move]:
        try:
            return self.tracker.legal_moves()
        except Exception:
            # The starter's en passant inference can raise; without the previous
            # observation it cannot, at the cost of not offering en passant.
            log("obscuro: legal move generation failed, retrying without en passant inference")
            traceback.print_exc(file=sys.stderr)
            return candidates(self.tracker.current, self.side, self.tracker.rights)[1]

    def _search(self, moves: list[chess.Move], remaining_time: float, spent: float) -> chess.Move:
        if self.move_time:
            budget = self.move_time
        else:
            # The belief update already used `spent` seconds of this turn's clock.
            budget = move_budget(remaining_time - spent, self.increment) - spent
        # A fixed --move-time is a deliberate choice (tests use tiny ones); the floor
        # only guards the clock-based budget.
        if not self.belief_ok or (not self.move_time and budget < MIN_SEARCH_SECONDS):
            log(f"obscuro: no search (belief_ok={self.belief_ok} budget={budget:.2f}s "
                f"belief_update={spent:.2f}s)")
            return self._fallback_move(moves)
        repeats = [self.played[self.tracker.current, move.uci()] for move in moves]
        result = search(self.belief.states, moves, self.side, budget, self.rng,
                        repeat_counts=repeats if any(repeats) else None)
        if result is None:
            log(f"obscuro: no usable root among {len(self.belief)} states")
            return self._fallback_move(moves)
        log(f"obscuro: {result.move.uci()} value={result.value:+.3f} gap={result.nash_gap:.3f} "
            f"|P|={len(self.belief)} roots={result.roots} iters={result.iterations} "
            f"repairs={self.belief.repairs} budget={budget:.2f}s belief_update={spent:.2f}s"
            + (" repeat_avoided" if result.repeat_avoided else ""))
        return result.move

    def _fallback_move(self, moves: list[chess.Move]) -> chess.Move:
        """Needs only the current observation: best capture that does not leave our
        king attacked by a piece we can see. Never raises."""
        self.fallbacks += 1
        try:
            board = candidates(self.tracker.current, self.side, self.tracker.rights)[0]

            def score(move: chess.Move) -> float:
                target = board.piece_at(move.to_square)
                value = FALLBACK_VALUES[target.piece_type] * 10 if target else 0
                if move.promotion:
                    value += FALLBACK_VALUES[move.promotion] * 5
                board.push(move)
                king = board.king(self.side)
                if king is not None and board.is_attacked_by(not self.side, king):
                    value -= 1000
                board.pop()
                return value + self.rng.random()

            return max(moves, key=score)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return self.rng.choice(moves)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-states", type=int, default=1500)
    parser.add_argument("--move-time", type=float, default=None,
                        help="fixed seconds per move instead of the clock-based budget")
    args = parser.parse_args()
    run(ObscuroAgent(args.seed, args.max_states, args.move_time))


if __name__ == "__main__":
    main()
