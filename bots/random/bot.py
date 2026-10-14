#!/usr/bin/env python3
"""Uniformly random Fog of War bot (port of the starter's uniform_random.py)."""
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

from fow.protocol import Agent, log, run  # noqa: E402
from uniform_random import ObservationTracker  # noqa: E402  (starter kit)


class RandomAgent(Agent):
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.tracker: ObservationTracker | None = None

    def reset(self, color: bool, base: float, inc: float) -> None:
        self.tracker = ObservationTracker(color)
        log(f"random: playing {'white' if color else 'black'} at {base:g}+{inc:g}")

    def observe(self, obs: str) -> None:
        self.tracker.observe(obs)

    def act(self, remaining_time: float) -> str | None:
        moves = self.tracker.legal_moves()
        if not moves:
            return None
        move = self.rng.choice(moves)
        self.tracker.record_move(move)
        return move.uci()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    run(RandomAgent(args.seed))


if __name__ == "__main__":
    main()
