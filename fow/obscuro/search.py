"""One move of search (section 7, reduced): sample roots, build, solve, pick.

The time budget is split: up to ``BUILD_SHARE`` of it adds sampled roots to the
subgame, and the rest runs PCFR+ on the finished subgame.
"""
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


def search(states: list[chess.Board], our_moves: list[chess.Move], side: chess.Color,
           budget: float, rng: random.Random) -> SearchResult | None:
    """Return the top action of the last PCFR+ iterate (top-1 purification, section 6.2).

    Returns None if no sampled state admits all of ``our_moves``.
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

    best = int(np.argmax(solver.ours.strategy))
    return SearchResult(our_moves[best], solver.value, solver.nash_gap(),
                        builder.n_roots, solver.iterations)
