"""choose_action avoids repeating a move only when we are winning."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fow.obscuro.search import AHEAD_VALUE, REPEAT_PENALTY, choose_action  # noqa: E402

STRATEGY = np.array([1.0, 0.0, 0.0])
VALUES = np.array([0.50, 0.48, 0.20])


def test_no_history_plays_the_top_action() -> None:
    assert choose_action(STRATEGY, VALUES, 0.5, None) == 0
    assert choose_action(STRATEGY, VALUES, 0.5, np.zeros(3)) == 0


def test_winning_and_repeating_switches_to_a_close_alternative() -> None:
    assert choose_action(STRATEGY, VALUES, 0.5, np.array([1.0, 0.0, 0.0])) == 1


def test_a_much_worse_alternative_is_not_taken() -> None:
    values = np.array([0.50, 0.50 - 1.5 * REPEAT_PENALTY, 0.20])
    assert choose_action(STRATEGY, values, 0.5, np.array([1.0, 0.0, 0.0])) == 0
    assert choose_action(STRATEGY, values, 0.5, np.array([2.0, 0.0, 0.0])) == 1


def test_not_ahead_keeps_repeating() -> None:
    counts = np.array([3.0, 0.0, 0.0])
    assert choose_action(STRATEGY, VALUES, AHEAD_VALUE, counts) == 0
    assert choose_action(STRATEGY, VALUES, -0.4, counts) == 0


def test_repeats_of_other_moves_do_not_change_the_choice() -> None:
    assert choose_action(STRATEGY, VALUES, 0.5, np.array([0.0, 2.0, 1.0])) == 0
