"""Empirical king hazard: how likely an unseen piece attacks our king after a move.

Fitted on 150 arena games of version 4 (5,858 decisions, 63 unseen attacks on the king,
each one a lost game). The features are the squares we cannot see from which a slider or
a knight could reach the king's square, counted on our view after the move, and the
opponent's material. A logistic fit, calibrated: mean prediction 1.08%, observed 1.08%.
By exposure the observed rate runs from 0.05% (nothing unseen in reach) to 16% (20 or
more unseen squares in reach).
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import chess

INTERCEPT = -7.99
ROOK_RAY = 0.356      # per unseen square on the king's ranks and files, up to the first seen piece
BISHOP_RAY = 0.383    # per unseen square on its diagonals
KNIGHT = -0.020       # per unseen knight square (no effect; kept for the fit's calibration)
MATERIAL = 0.078      # per point of opponent material (queen 9, rook 5, bishop 3, knight 3)
MATERIAL_VALUE = {chess.QUEEN: 9, chess.ROOK: 5, chess.BISHOP: 3, chess.KNIGHT: 3}
DEFAULT_MATERIAL = 31.0  # the opening value, used when no belief sample is at hand

RAYS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def exposure(view: Sequence[str], king: int) -> tuple[int, int, int]:
    """(rook-ray, bishop-ray, knight) unseen squares from which `king` could be attacked.
    A seen empty square lets a ray pass; a seen piece stops it."""
    rook = bishop = 0
    for df, dr in RAYS:
        f, r = chess.square_file(king) + df, chess.square_rank(king) + dr
        while 0 <= f < 8 and 0 <= r < 8:
            c = view[chess.square(f, r)]
            if c == "?":
                if df == 0 or dr == 0:
                    rook += 1
                else:
                    bishop += 1
            elif c != "-":
                break
            f += df
            r += dr
    knight = sum(1 for s in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[king]) if view[s] == "?")
    return rook, bishop, knight


def hazard(view: Sequence[str], king: int, opp_material: float) -> float:
    rook, bishop, knight = exposure(view, king)
    z = INTERCEPT + ROOK_RAY * rook + BISHOP_RAY * bishop + KNIGHT * knight + MATERIAL * opp_material
    return min(0.75, 1.0 / (1.0 + math.exp(-z)))  # beyond the data at the top: capped


def opponent_material(states: Sequence[chess.Board], side: chess.Color,
                      weights: Sequence[float] | None = None) -> float:
    """Weighted mean of the opponent's material over a belief sample."""
    if not states:
        return DEFAULT_MATERIAL
    total = weighed = 0.0
    for i, board in enumerate(states):
        w = weights[i] if weights is not None and i < len(weights) else 1.0
        if w <= 0:
            continue
        material = sum(len(board.pieces(pt, not side)) * v for pt, v in MATERIAL_VALUE.items())
        total += w
        weighed += w * material
    return weighed / total if total > 0 else DEFAULT_MATERIAL


def move_hazards(view: str, side: chess.Color, moves: Sequence[chess.Move],
                 opp_material: float) -> list[float]:
    """Per candidate move, the hazard of the square our king stands on after it, judged on
    our current view with the move applied to our own pieces."""
    own_king = next((s for s in range(64) if view[s] == ("K" if side else "k")), None)
    out = []
    for move in moves:
        after = list(view)
        piece = view[move.from_square]
        after[move.from_square] = "-"
        after[move.to_square] = piece if move.promotion is None else (
            chess.piece_symbol(move.promotion).upper() if side else chess.piece_symbol(move.promotion))
        king = own_king
        if piece.upper() == "K":
            king = move.to_square
            if abs(chess.square_file(move.to_square) - chess.square_file(move.from_square)) == 2:
                rank = chess.square_rank(move.from_square)   # castling: the rook moves too
                if chess.square_file(move.to_square) == 6:
                    after[chess.square(7, rank)] = "-"
                    after[chess.square(5, rank)] = "R" if side else "r"
                else:
                    after[chess.square(0, rank)] = "-"
                    after[chess.square(3, rank)] = "R" if side else "r"
        out.append(hazard(after, king, opp_material) if king is not None else 0.0)
    return out
