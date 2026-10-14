#!/usr/bin/env python3
"""Greedy Fog of War bot: prefers captures and promotions (port of baseline.py).

Unlike the starter baseline it reuses the starter's ObservationTracker, so it
also infers en passant from consecutive observations.
"""
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

from fow.protocol import Agent, log, run  # noqa: E402
from uniform_random import ObservationTracker, candidates  # noqa: E402  (starter kit)

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


class GreedyAgent(Agent):
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.tracker: ObservationTracker | None = None

    def reset(self, color: bool, base: float, inc: float) -> None:
        self.tracker = ObservationTracker(color)
        log(f"greedy: playing {'white' if color else 'black'} at {base:g}+{inc:g}")

    def observe(self, obs: str) -> None:
        self.tracker.observe(obs)

    def act(self, remaining_time: float) -> str | None:
        tracker = self.tracker
        board, moves = candidates(tracker.current, tracker.side, tracker.rights, tracker.previous)
        if not moves:
            return None

        def score(move: chess.Move) -> float:
            target = board.piece_at(move.to_square)
            value = PIECE_VALUES[target.piece_type] * 10 if target else 0
            if move.promotion:
                value += PIECE_VALUES[move.promotion] * 5
            return value + self.rng.random()

        move = max(moves, key=score)
        tracker.record_move(move)
        return move.uci()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    run(GreedyAgent(args.seed))


if __name__ == "__main__":
    main()
