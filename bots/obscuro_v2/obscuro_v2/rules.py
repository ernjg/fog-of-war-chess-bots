"""Terminal checks, matching the referee's ``outcome``."""
from __future__ import annotations

import chess


def side_to_move_wins(board: chess.Board) -> bool:
    """The side to move can capture the opposing king, so the game is already over."""
    king = board.king(not board.turn)
    return king is None or board.is_attacked_by(board.turn, king)
