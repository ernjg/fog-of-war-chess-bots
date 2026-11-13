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
REPEAT_PENALTY = 0.05  # value given up per earlier play of the same move from the same view


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


def choose_action(strategy: np.ndarray, action_values: np.ndarray, value: float,
                  repeat_counts: np.ndarray | None) -> int:
    """The top action of ``strategy``, unless that would repeat ourselves while winning.

    ``repeat_counts[a]`` is how often we already played move ``a`` from this exact
    observation. Repeating it invites a draw by threefold repetition, so when we are
    ahead each earlier play costs the move REPEAT_PENALTY and the best-valued move
    after that discount is played instead. When we are not ahead, nothing changes.
    """
    best = int(np.argmax(strategy))
    if repeat_counts is None or value <= AHEAD_VALUE or repeat_counts[best] == 0:
        return best
    return int(np.argmax(action_values - REPEAT_PENALTY * repeat_counts))


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
