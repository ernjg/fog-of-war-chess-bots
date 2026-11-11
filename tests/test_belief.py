"""The belief set always contains the true position (Proposition 1) when the cap is not hit."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from fow.obscuro.belief import Belief, project, state_key  # noqa: E402
from fow.obscuro.rules import side_to_move_wins  # noqa: E402
from referee import FowBoard, fow_moves, observation  # noqa: E402


def random_game(seed: int, plies: int):
    """Yield (board after the ply, mover, move) for a random game that avoids losing at once."""
    rng = random.Random(seed)
    board = FowBoard()
    for _ in range(plies):
        safe = [move for move in fow_moves(board) if not _loses_immediately(board, move)]
        if not safe:
            return
        move = rng.choice(safe)
        mover = board.turn
        board.push(move)
        yield board, mover, move


def _loses_immediately(board: FowBoard, move: chess.Move) -> bool:
    board.push(move)
    try:
        return side_to_move_wins(board)
    finally:
        board.pop()


@pytest.mark.parametrize("side", [chess.WHITE, chess.BLACK])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_true_state_stays_in_belief(side: chess.Color, seed: int) -> None:
    belief = Belief(side, max_states=10**6)
    belief.observe(observation(FowBoard(), side))
    for board, mover, move in random_game(seed, plies=24):
        belief.observe(observation(board, side), own_move=move if mover == side else None)
        assert state_key(board) in {state_key(state) for state in belief.states}
    assert belief.repairs == 0


def test_capped_belief_never_empties_and_agrees_with_view() -> None:
    side = chess.WHITE
    belief = Belief(side, max_states=1, rng=random.Random(0))
    belief.observe(observation(FowBoard(), side))
    for board, mover, move in random_game(3, plies=40):
        obs = observation(board, side)
        belief.observe(obs, own_move=move if mover == side else None)
        assert belief.states
        for state in belief.states:
            for square, char in enumerate(obs):
                if char != "?":
                    piece = state.piece_at(square)
                    assert (piece.symbol() if piece else "-") == char


def test_project_writes_observation_and_keeps_one_king() -> None:
    board = FowBoard()
    obs = observation(board, chess.WHITE)
    fixed = project(FowBoard(None), obs, chess.WHITE, chess.WHITE)
    assert all(fixed.piece_at(sq) is not None for sq in range(16))
    assert len(fixed.pieces(chess.KING, chess.BLACK)) == 1
