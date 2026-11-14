"""Repetition: what counts as going back (own_placement) and what it costs (choose_action)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402

from fow.obscuro.search import (AHEAD_VALUE, DRAW_SHARE, REPEAT_PENALTY, choose_action,  # noqa: E402
                                own_placement)
from referee import FowBoard, observation  # noqa: E402

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


def test_a_third_time_costs_a_share_of_the_lead() -> None:
    """Going back a second time may make the position's third occurrence: a draw. Far
    ahead, a clearly worse move is better than that, but not one that loses the king."""
    values = np.array([0.90, 0.60, -1.0])
    assert choose_action(STRATEGY, values, 0.9, np.array([1.0, 0.0, 0.0])) == 0  # the first time back: 0.85
    assert choose_action(STRATEGY, values, 0.9, np.array([2.0, 0.0, 0.0])) == 1  # 0.90 - 0.45 against 0.60
    assert DRAW_SHARE * 0.9 > 0.90 - 0.60
    assert choose_action(STRATEGY, np.array([0.90, -1.0, -1.0]), 0.9, np.array([2.0, 0.0, 0.0])) == 0
    # Barely ahead there is little to give up: two penalties, as before.
    close = np.array([0.15, 0.15 - 2.5 * REPEAT_PENALTY, 0.0])
    assert choose_action(STRATEGY, close, 0.15, np.array([2.0, 0.0, 0.0])) == 0


def test_not_ahead_keeps_repeating() -> None:
    counts = np.array([3.0, 0.0, 0.0])
    assert choose_action(STRATEGY, VALUES, AHEAD_VALUE, counts) == 0
    assert choose_action(STRATEGY, VALUES, -0.4, counts) == 0


def test_repeats_of_other_moves_do_not_change_the_choice() -> None:
    assert choose_action(STRATEGY, VALUES, 0.5, np.array([0.0, 2.0, 1.0])) == 0


def test_own_placement_is_our_pieces_and_nothing_else() -> None:
    board = FowBoard()
    white = own_placement(observation(board, chess.WHITE), chess.WHITE)
    assert white == "RNBQKBNRPPPPPPPP" + "-" * 48
    assert own_placement(observation(board, chess.BLACK), chess.BLACK) == "-" * 48 + "pppppppprnbqkbnr"
    board.push_uci("e2e4")
    board.push_uci("d7d5")   # now White sees a black pawn: it is not part of the placement
    view = observation(board, chess.WHITE)
    assert "p" in view and "p" not in own_placement(view, chess.WHITE)


def test_own_placement_after_a_move_is_what_the_board_becomes() -> None:
    """Every kind of move, against the board itself: ordinary, capture, castling either
    way and either colour, promotion, en passant."""
    lines = [
        ["e2e4", "d7d5", "e4d5", "d8d5", "g1f3", "d5a5", "f1e2", "c8g4", "e1g1", "b8c6", "d2d4", "e8c8"],
        ["a2a4", "h7h5", "a4a5", "h5h4", "a5a6", "h4h3", "a6b7", "h3g2", "b7a8q", "g2h1n"],
        ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"],
        ["d2d4", "g8f6", "c1f4", "g7g6", "b1c3", "f8g7", "d1d2", "e8g8", "e1c1"],
    ]
    for line in lines:
        board = FowBoard()
        for uci in line:
            side, move = board.turn, chess.Move.from_uci(uci)
            predicted = own_placement(observation(board, side), side, move)
            board.push(move)
            assert predicted == own_placement(observation(board, side), side), (line, uci)


def test_the_same_squares_by_another_move_count_as_going_back() -> None:
    """What the old rule missed: a rook that reaches d5 from c5 and later from d4 has made
    the same position twice, although no move was played twice."""
    board = FowBoard("7k/8/8/2R5/8/8/8/K7 w - - 0 1")
    there = own_placement(observation(board, chess.WHITE), chess.WHITE, chess.Move.from_uci("c5d5"))
    board.set_fen("7k/8/8/8/3R4/8/8/K7 w - - 0 1")
    assert own_placement(observation(board, chess.WHITE), chess.WHITE, chess.Move.from_uci("d4d5")) == there
    assert own_placement(observation(board, chess.WHITE), chess.WHITE, chess.Move.from_uci("d4d6")) != there
