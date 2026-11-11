"""PCFR+ on hand-built depth-2 games with known equilibria, and on a real position."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from fow.obscuro.search import search  # noqa: E402
from fow.obscuro.solver import Depth2Solver  # noqa: E402
from fow.obscuro.subgame import Depth2Game  # noqa: E402
from referee import FowBoard  # noqa: E402


def one_root_game(payoff: np.ndarray, hidden: bool) -> Depth2Game:
    """One root, our moves = rows, opponent replies = columns of ``payoff``.

    hidden=True puts both opponent nodes in one infoset (it cannot see our move);
    hidden=False gives each its own infoset (perfect information).
    """
    n_ours, n_theirs = payoff.shape
    infoset_of_node = [0] * n_ours if hidden else list(range(n_ours))
    n_infosets = max(infoset_of_node) + 1
    return Depth2Game(
        root_weight=np.array([1.0]),
        n_actions=n_ours,
        terminal_value=np.full(n_ours, np.nan),
        leaf_node=np.repeat(np.arange(n_ours), n_theirs),
        leaf_slot=np.array([infoset_of_node[a] * n_theirs + b
                            for a in range(n_ours) for b in range(n_theirs)]),
        leaf_value=payoff.ravel().astype(float),
        slot_infoset=np.repeat(np.arange(n_infosets), n_theirs),
        infoset_start=np.arange(n_infosets) * n_theirs,
        our_prior=np.zeros(n_ours),
        their_prior=np.zeros(n_infosets * n_theirs),
    )


def solve(game: Depth2Game, iterations: int) -> Depth2Solver:
    solver = Depth2Solver(game)
    for _ in range(iterations):
        solver.iterate()
    return solver


def test_matching_pennies_hidden_move_mixes() -> None:
    solver = solve(one_root_game(np.array([[1, -1], [-1, 1]]), hidden=True), 2000)
    assert solver.nash_gap() < 0.02
    assert abs(solver.value) < 0.02
    assert np.allclose(solver.ours.strategy, 0.5, atol=0.05)


def test_matching_pennies_visible_move_loses() -> None:
    solver = solve(one_root_game(np.array([[1, -1], [-1, 1]]), hidden=False), 200)
    assert solver.nash_gap() < 1e-6
    assert solver.value == -1.0


def test_random_hidden_game_converges() -> None:
    payoff = np.random.default_rng(0).uniform(-1, 1, size=(6, 5))
    solver = solve(one_root_game(payoff, hidden=True), 5000)
    assert solver.nash_gap() < 0.01


def test_search_returns_a_legal_move_from_the_start() -> None:
    board = FowBoard()
    moves = list(board.generate_pseudo_legal_moves())
    result = search([board], moves, chess.WHITE, budget=0.2, rng=random.Random(0))
    assert result is not None and result.move in moves
