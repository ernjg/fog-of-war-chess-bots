"""The belief set P: every position consistent with our observations (section 2).

P is filtered exactly (section 2.1) but capped at ``max_states`` by uniform
subsampling. The cap can drop the true position; if no state then survives an
observation, the previous states are projected onto it (``project``) so the bot
keeps a plausible belief instead of an empty one.
"""
from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Iterator

import chess

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard, fow_moves, observation

from .rules import side_to_move_wins

StateKey = tuple


def state_key(board: chess.Board) -> StateKey:
    """The state tuple (B, t, c, e) from section 1.1, as bitboards."""
    return (board.pawns, board.knights, board.bishops, board.rooks, board.queens,
            board.kings, board.occupied_co[chess.WHITE], board.occupied_co[chess.BLACK],
            board.turn, board.castling_rights, board.ep_square)


class VisibleSquares:
    """One observation as bitboards, to reject candidates before the exact check."""

    def __init__(self, obs: str):
        self.visible = 0
        self.pieces: dict[tuple[chess.PieceType, chess.Color], int] = {
            (piece, color): 0 for piece in chess.PIECE_TYPES for color in chess.COLORS}
        for square, char in enumerate(obs):
            if char == "?":
                continue
            self.visible |= chess.BB_SQUARES[square]
            if char != "-":
                piece = chess.Piece.from_symbol(char)
                self.pieces[piece.piece_type, piece.color] |= chess.BB_SQUARES[square]
        self.occupied = 0
        for mask in self.pieces.values():
            self.occupied |= mask

    def agrees_with(self, board: chess.Board) -> bool:
        if board.occupied & self.visible != self.occupied:
            return False
        return all(board.pieces_mask(piece, color) & self.visible == mask
                   for (piece, color), mask in self.pieces.items())


class Belief:
    def __init__(self, side: chess.Color, max_states: int = 1500,
                 rng: random.Random | None = None):
        self.side = side
        self.max_states = max_states
        self.rng = rng or random.Random()
        self.states: list[FowBoard] = [FowBoard()]
        self.repairs = 0
        self._started = False

    def __len__(self) -> int:
        return len(self.states)

    def observe(self, obs: str, own_move: chess.Move | None = None) -> None:
        """Filter P with the observation that follows one ply (section 2.1).

        ``own_move`` is our move if we played the ply, else None (the opponent
        played it, or this is the first observation of the game).
        """
        if own_move is not None:
            candidates = self._successors(
                lambda board: (own_move,) if own_move in fow_moves(board) else ())
            to_move = not self.side
        elif self._started:
            candidates = self._successors(fow_moves)
            to_move = self.side
        else:
            candidates = iter(self.states)
            to_move = chess.WHITE
        self._started = True

        survivors = self._consistent(candidates, obs)
        if not survivors:
            self.repairs += 1
            survivors = self._unique(project(board, obs, self.side, to_move)
                                     for board in self.states)
        if len(survivors) > self.max_states:
            survivors = self.rng.sample(survivors, self.max_states)
        self.states = survivors

    def _successors(self, moves_of: Callable[[FowBoard], Iterable[chess.Move]]
                    ) -> Iterator[FowBoard]:
        """Each successor is yielded in place (pushed) and popped on resumption."""
        for board in self.states:
            for move in moves_of(board):
                board.push(move)
                yield board
                board.pop()

    def _consistent(self, boards: Iterable[FowBoard], obs: str) -> list[FowBoard]:
        view = VisibleSquares(obs)
        found: dict[StateKey, FowBoard] = {}
        for board in boards:
            if (not side_to_move_wins(board) and view.agrees_with(board)
                    and observation(board, self.side) == obs):
                found.setdefault(state_key(board), board.copy(stack=False))
        return list(found.values())

    @staticmethod
    def _unique(boards: Iterable[FowBoard]) -> list[FowBoard]:
        return list({state_key(board): board for board in boards}.values())


def project(board: FowBoard, obs: str, side: chess.Color, to_move: chess.Color) -> FowBoard:
    """Overwrite ``board`` with everything ``obs`` shows; keep its guesses elsewhere."""
    fixed = board.copy(stack=False)
    fixed.turn = to_move
    fixed.ep_square = None
    for square, char in enumerate(obs):
        if char == "?":
            piece = fixed.piece_at(square)
            if piece is not None and piece.color == side:
                fixed.remove_piece_at(square)  # our pieces are always visible
        elif char == "-":
            fixed.remove_piece_at(square)
        else:
            fixed.set_piece_at(square, chess.Piece.from_symbol(char))
    _keep_one_opponent_king(fixed, obs, side)
    fixed.castling_rights = fixed.clean_castling_rights()
    return fixed


def _keep_one_opponent_king(board: FowBoard, obs: str, side: chess.Color) -> None:
    opponent = not side
    kings = list(board.pieces(chess.KING, opponent))
    shown = [square for square in kings if obs[square] != "?"]
    keep = shown[0] if shown else (kings[0] if kings else None)
    for square in kings:
        if square != keep:
            board.remove_piece_at(square)
    if keep is None:
        home = chess.E8 if opponent == chess.BLACK else chess.E1
        hidden = [square for square in chess.SQUARES if obs[square] == "?"]
        nearest = min(hidden, key=lambda square: chess.square_distance(square, home))
        board.set_piece_at(nearest, chess.Piece(chess.KING, opponent))
