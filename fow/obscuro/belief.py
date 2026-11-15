"""The belief set: every position consistent with our observations, capped in size."""
from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterable, Iterator

import chess

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard, fow_moves, observation

from .rules import side_to_move_wins

StateKey = tuple

MIN_POOL = 128            # once the set is only a sample, keep at least this many states in it
# Unseen opponent moves that separate a new state from an old one: mostly a few, sometimes
# many, so that the sample also reaches what a few moves cannot (a king on the other wing).
WALK_STEPS = (1, 1, 2, 2, 3, 3, 5, 8)
REPLENISH_SECONDS = 0.1   # at most, per observation, for topping the sample up
MAX_MISSES = 64           # failed attempts in a row before concluding it cannot grow


def state_key(board: chess.Board) -> StateKey:
    """Hashable identity of a position: piece bitboards, side to move, castling, en passant."""
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
        self.exact = True  # False once the cap or a repair may have dropped the true position
        self._started = False
        self._unchecked = False  # the states come from a repair and may not fit the view
        self.update_cost = (0.0, 0)  # seconds the last filtering pass took, and for how many states

    def __len__(self) -> int:
        return len(self.states)

    def observe(self, obs: str, own_move: chess.Move | None = None) -> None:
        """Filter with the observation after one ply; ``own_move`` is None unless we played it."""
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

        parents, started = len(self.states), time.monotonic()
        survivors = self._consistent(candidates, obs)
        self.update_cost = (time.monotonic() - started, parents)
        if not survivors:
            survivors = self._repaired(obs, to_move)
        self._keep(survivors, obs)

    def repair(self, obs: str, to_move: chess.Color) -> None:
        """Rebuild the set from the current observation alone, when updating it failed."""
        self._started = True
        self._keep(self._repaired(obs, to_move), obs)

    def limit(self, max_states: int) -> None:
        """Change the cap. A larger set is cut down to it at once, by the same uniform
        subsampling as after an update, and is from then on only a sample."""
        self.max_states = max_states
        if len(self.states) > max_states:
            self.exact = False
            self.states = self.rng.sample(self.states, max_states)

    def _repaired(self, obs: str, to_move: chess.Color) -> list[FowBoard]:
        self.repairs += 1
        self.exact = False
        self._unchecked = True
        return self._unique(
            fit_to_view(project(board, obs, self.side, to_move), obs, self.side, self.rng)
            for board in self.states)

    def _keep(self, survivors: list[FowBoard], obs: str) -> None:
        if len(survivors) > self.max_states:
            self.exact = False
            survivors = self.rng.sample(survivors, self.max_states)
        self.states = survivors
        self.replenish(obs)

    def replenish(self, obs: str) -> None:
        """Keep a sampled belief from collapsing onto a few states.

        While the set is exact, a small set is knowledge. Once the cap has dropped states
        (most likely the true one among them), each later observation kills off most of
        what is left, and a handful of survivors would be read as near-certainty about the
        hidden pieces. So a thin sample is topped up with states that differ from existing
        ones by a few opponent moves made out of our sight, each checked to produce exactly
        the current observation. They need not fit the earlier observations: the sample
        stands for what we cannot see, not for one history.

        States left by a repair only agree with the squares we see; they can still imply
        a different view. Whenever some state fits the view exactly, only those are kept
        and the top-up starts from them; the others remain only if nothing fits. Checking
        them comes out of the same time allowance: what is not checked in time is treated
        like what does not fit.
        """
        target = min(MIN_POOL, self.max_states)
        hidden = sum(chess.BB_SQUARES[square] for square, char in enumerate(obs) if char == "?")
        if self.exact or not self.states or not hidden:
            return
        if len(self.states) >= target and not self._unchecked:
            return  # filtered exactly by this observation, and plenty of them
        deadline = time.monotonic() + REPLENISH_SECONDS

        def fits(board: FowBoard) -> bool:
            return not side_to_move_wins(board) and observation(board, self.side) == obs

        if self._unchecked:  # there may be many: in random order, as far as the time goes
            pool: list[FowBoard] = []
            for board in self.rng.sample(self.states, len(self.states)):
                if time.monotonic() >= deadline:
                    break
                if fits(board):
                    pool.append(board)
        else:                # observe() has just filtered them with this very check
            pool = list(self.states)
        self._unchecked = False
        seeds = pool or self.states  # walk from states that fit, if there are any
        seen = {state_key(board) for board in self.states}
        misses = 0
        while len(pool) < target and misses < MAX_MISSES and time.monotonic() < deadline:
            board = self.rng.choice(pool or seeds).copy(stack=False)
            if self._walk_in_fog(board, hidden) and state_key(board) not in seen and fits(board):
                seen.add(state_key(board))
                pool.append(board)
                misses = 0
            else:
                misses += 1
        if pool:
            self.states = pool

    def _walk_in_fog(self, board: FowBoard, hidden: int) -> bool:
        """Move opponent pieces that we cannot see to other squares we cannot see, by
        ordinary non-capturing moves (castling included). Returns whether anything moved.
        The caller checks that the result still produces our observation."""
        opponent = not self.side
        targets = hidden
        if board.ep_square is not None:
            # A pawn that has just made its double step cannot have something behind it
            # on the square it came from. (Stockfish would not allow the capture then.)
            for origin in (board.ep_square + 8, board.ep_square - 8):
                if 0 <= origin < 64:
                    targets &= ~chess.BB_SQUARES[origin]
        to_move, board.turn = board.turn, opponent
        moved = False
        try:
            for _ in range(self.rng.choice(WALK_STEPS)):
                pieces = list(chess.scan_forward(board.occupied_co[opponent] & hidden))
                if not pieces:
                    break
                origin = chess.BB_SQUARES[self.rng.choice(pieces)]
                moves = [move for move in board.generate_pseudo_legal_moves(origin, targets & ~board.occupied)
                         if not (move.promotion or board.is_en_passant(move))]
                if not moves:
                    continue
                move = self.rng.choice(moves)
                if board.is_castling(move):
                    rank = chess.square_rank(move.from_square)
                    kingside = move.to_square > move.from_square
                    board.set_piece_at(chess.square(5 if kingside else 3, rank),
                                       board.remove_piece_at(chess.square(7 if kingside else 0, rank)))
                board.set_piece_at(move.to_square, board.remove_piece_at(move.from_square))
                moved = True
        finally:
            board.turn = to_move
        if moved:
            board.castling_rights = board.clean_castling_rights()
            if board.ep_square is not None and not board.has_pseudo_legal_en_passant():
                board.ep_square = None  # the pawn it referred to may have walked on
        return moved

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
    _drop_double_counted(fixed, board, obs, side)
    fixed.castling_rights = fixed.clean_castling_rights()
    return fixed


def _drop_double_counted(fixed: FowBoard, old: FowBoard, obs: str, side: chess.Color) -> None:
    """Take out the old guess for a piece that has now come into view.

    A piece we see for the first time stood somewhere out of sight a move ago, and
    ``old`` still has it there. With the view written over it, ``fixed`` counts that piece
    twice. So for each kind of opponent piece, as many unseen ones are removed as the
    board has gained, nearest first to the squares where one of that kind appeared. The
    same is done until the material is possible at all (eight pawns at most, and one pawn
    fewer for every piece beyond the starting set): Stockfish does not take anything else.
    """
    opponent = not side

    def unseen(kind: chess.PieceType) -> list[chess.Square]:
        return [square for square in fixed.pieces(kind, opponent) if obs[square] == "?"]

    def remove_nearest(kind: chess.PieceType, arrived: list[chess.Square]) -> bool:
        hidden = unseen(kind)
        if not hidden:
            return False
        fixed.remove_piece_at(min(hidden, key=lambda square: (
            min((chess.square_distance(square, other) for other in arrived), default=0), square)))
        return True

    kinds = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    for kind in kinds:
        piece = chess.Piece(kind, opponent)
        arrived = [square for square in fixed.pieces(kind, opponent)
                   if obs[square] != "?" and old.piece_at(square) != piece]
        for _ in range(len(fixed.pieces(kind, opponent)) - len(old.pieces(kind, opponent))):
            if not remove_nearest(kind, arrived):
                break

    start = {chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}
    while True:
        count = {kind: len(fixed.pieces(kind, opponent)) for kind in kinds}
        over = [kind for kind in start if count[kind] > start[kind]]
        if count[chess.PAWN] + sum(count[kind] - start[kind] for kind in over) <= 8:
            break
        if not any(remove_nearest(kind, []) for kind in (chess.PAWN, *over)):
            break  # everything beyond the limit is in plain view: nothing left to correct


def fit_to_view(board: FowBoard, obs: str, side: chess.Color, rng: random.Random) -> FowBoard:
    """Make a projected board agree with what the fog tells us through our pawns.

    A square we cannot see straight ahead of one of our pawns holds an opponent piece
    (the pawn could otherwise step there, and we would see the square). An unseen square
    that one of our pawns attacks holds none (the pawn could otherwise capture, and we
    would see it). Unseen opponent pieces are moved to make both true. Changes ``board``.
    """
    opponent = not side
    step = 8 if side == chess.WHITE else -8
    home_rank = 1 if side == chess.WHITE else 6
    hidden = sum(chess.BB_SQUARES[square] for square, char in enumerate(obs) if char == "?")
    blocked: list[chess.Square] = []  # unseen squares that must be occupied
    banned = 0                        # unseen squares that must be empty
    for pawn in board.pieces(chess.PAWN, side):
        banned |= chess.BB_PAWN_ATTACKS[side][pawn] & hidden
        ahead = pawn + step
        if not 0 <= ahead < 64:
            continue
        if obs[ahead] == "?":
            blocked.append(ahead)
        elif obs[ahead] == "-" and chess.square_rank(pawn) == home_rank and obs[ahead + step] == "?":
            blocked.append(ahead + step)  # the double step is what is blocked
    unfilled = [square for square in blocked if board.piece_at(square) is None]
    offenders = list(chess.scan_forward(board.occupied_co[opponent] & banned))
    if not unfilled and not offenders:
        return board

    def may_stand(piece_type: chess.PieceType, square: chess.Square) -> bool:
        return piece_type != chess.PAWN or 0 < chess.square_rank(square) < 7

    spare = [square for square in chess.scan_forward(hidden & ~board.occupied & ~banned)
             if square not in blocked]
    rng.shuffle(spare)
    rng.shuffle(unfilled)
    for origin in offenders:  # off the squares our pawns attack: where a blocker is missing, else anywhere unseen
        piece = board.remove_piece_at(origin)
        for places in (unfilled, spare):
            target = next((sq for sq in places if may_stand(piece.piece_type, sq)), None)
            if target is not None:
                places.remove(target)
                board.set_piece_at(target, piece)
                break
        else:
            if piece.piece_type == chess.KING:
                board.set_piece_at(origin, piece)  # nowhere to go: better a misfit than no king
    for target in unfilled:   # blockers still missing: any other unseen opponent piece will do
        donors = [square for square in chess.scan_forward(board.occupied_co[opponent] & hidden & ~board.kings)
                  if square not in blocked and may_stand(board.piece_type_at(square), target)]
        if donors:
            board.set_piece_at(target, board.remove_piece_at(rng.choice(donors)))
        else:
            kind = chess.PAWN if may_stand(chess.PAWN, target) else chess.KNIGHT
            board.set_piece_at(target, chess.Piece(kind, opponent))
    board.castling_rights = board.clean_castling_rights()
    return board


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
