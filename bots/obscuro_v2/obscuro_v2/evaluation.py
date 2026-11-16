"""Heuristic leaf value: material plus visible squares, squashed into [-1, 1]."""
from __future__ import annotations

import math

import chess

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
VISIBILITY_WEIGHT = 0.05  # pawns per visible square
SCALE = 5.0               # a 5-pawn advantage maps to tanh(1) = 0.76


def material(board: chess.Board, color: chess.Color) -> int:
    return sum(value * board.pieces_mask(piece, color).bit_count()
               for piece, value in PIECE_VALUES.items())


def visible_squares(board: chess.Board, color: chess.Color) -> int:
    seen = board.occupied_co[color]
    for square in chess.scan_forward(board.occupied_co[color]):
        seen |= board.attacks_mask(square)
    return seen.bit_count()


def evaluate(board: chess.Board, perspective: chess.Color) -> float:
    advantage = (material(board, perspective) - material(board, not perspective)
                 + VISIBILITY_WEIGHT * (visible_squares(board, perspective)
                                        - visible_squares(board, not perspective)))
    return math.tanh(advantage / SCALE)
