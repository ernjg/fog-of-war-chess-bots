#!/usr/bin/env python3
"""Reduced Obscuro: belief set + depth-2 imperfect-information subgame + PCFR+."""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Make `fow` importable from the flat packaged layout (fow/ next to bot.py)
# or from the repo layout (bots/<name>/bot.py with fow/ at the repo root).
_HERE = Path(__file__).resolve().parent
for _root in (_HERE, *_HERE.parents[1:2]):
    if (_root / "fow").is_dir() and str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import chess  # noqa: E402

from fow.obscuro.belief import Belief  # noqa: E402
from fow.obscuro.search import move_budget, search  # noqa: E402
from fow.protocol import Agent, log, run  # noqa: E402
from uniform_random import ObservationTracker  # noqa: E402  (starter kit)


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
        log(f"obscuro: playing {'white' if color else 'black'} at {base:g}+{inc:g}")

    def observe(self, obs: str) -> None:
        self.tracker.observe(obs)
        self.belief.observe(obs, own_move=self.last_move)
        self.last_move = None

    def act(self, remaining_time: float) -> str | None:
        moves = self.tracker.legal_moves()
        if not moves:
            return None
        move = moves[0] if len(moves) == 1 else self._search(moves, remaining_time)
        self.tracker.record_move(move)
        self.last_move = move
        return move.uci()

    def _search(self, moves: list[chess.Move], remaining_time: float) -> chess.Move:
        budget = self.move_time or move_budget(remaining_time, self.increment)
        result = search(self.belief.states, moves, self.side, budget, self.rng)
        if result is None:
            log(f"obscuro: no usable root among {len(self.belief)} states, playing at random")
            return self.rng.choice(moves)
        log(f"obscuro: {result.move.uci()} value={result.value:+.3f} gap={result.nash_gap:.3f} "
            f"|P|={len(self.belief)} roots={result.roots} iters={result.iterations} "
            f"repairs={self.belief.repairs} budget={budget:.2f}s")
        return result.move


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
