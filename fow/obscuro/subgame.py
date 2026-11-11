"""The depth-2 subgame, stored as flat arrays (layout in docs/obscuro.md)."""
from __future__ import annotations

from dataclasses import dataclass

import chess
import numpy as np

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard, fow_moves, observation

from .evaluation import evaluate
from .rules import side_to_move_wins

WIN, LOSS = 1.0, -1.0


@dataclass(frozen=True)
class Depth2Game:
    root_weight: np.ndarray        # (R,)    chance probability of each root
    n_actions: int                 # A       our legal moves
    terminal_value: np.ndarray     # (R*A,)  value of a terminal opponent node, NaN otherwise
    leaf_node: np.ndarray          # (L,)    opponent node j of each leaf
    leaf_slot: np.ndarray          # (L,)    opponent slot (infoset, reply) of each leaf
    leaf_value: np.ndarray         # (L,)
    slot_infoset: np.ndarray       # (S,)    infoset of each slot, contiguous blocks
    infoset_start: np.ndarray      # (J,)    first slot of each infoset
    our_prior: np.ndarray          # (A,)    heuristic value of each of our moves
    their_prior: np.ndarray        # (S,)    mean leaf value of each opponent reply

    @property
    def n_roots(self) -> int:
        return len(self.root_weight)


class SubgameBuilder:
    """Adds sampled roots one at a time, so the caller can stop when time runs out."""

    def __init__(self, our_moves: list[chess.Move], side: chess.Color):
        self.our_moves = our_moves
        self.side = side
        self.n_roots = 0
        self._infosets: dict[tuple, tuple[int, int]] = {}  # key -> (first slot, n replies)
        self._slot_infoset: list[int] = []
        self._terminal: list[float] = []
        self._our_prior = np.zeros(len(our_moves))
        self._leaf_node: list[int] = []
        self._leaf_slot: list[int] = []
        self._leaf_value: list[float] = []

    def add_root(self, root: FowBoard) -> bool:
        """Add ``root`` unless one of our moves is illegal there (it contradicts our view)."""
        if not set(self.our_moves) <= set(fow_moves(root)):
            return False
        board = root.copy(stack=False)
        for action, move in enumerate(self.our_moves):
            node = self.n_roots * len(self.our_moves) + action
            board.push(move)
            self._our_prior[action] += evaluate(board, self.side)
            self._terminal.append(self._add_opponent_node(board, node))
            board.pop()
        self.n_roots += 1
        return True

    def _add_opponent_node(self, board: FowBoard, node: int) -> float:
        """Add the opponent's replies at ``board``; return its value if terminal, else NaN."""
        if side_to_move_wins(board):
            return LOSS
        replies = sorted(fow_moves(board), key=chess.Move.uci)
        if not replies:
            return WIN
        first_slot = self._infoset_slots(board, replies)
        for offset, reply in enumerate(replies):
            board.push(reply)
            self._leaf_node.append(node)
            self._leaf_slot.append(first_slot + offset)
            self._leaf_value.append(WIN if side_to_move_wins(board) else evaluate(board, self.side))
            board.pop()
        return np.nan

    def _infoset_slots(self, board: FowBoard, replies: list[chess.Move]) -> int:
        key = (observation(board, not self.side), tuple(move.uci() for move in replies))
        if key not in self._infosets:
            infoset = len(self._infosets)
            self._infosets[key] = (len(self._slot_infoset), len(replies))
            self._slot_infoset.extend([infoset] * len(replies))
        return self._infosets[key][0]

    def build(self) -> Depth2Game:
        leaf_slot = np.array(self._leaf_slot, dtype=np.int64)
        leaf_value = np.array(self._leaf_value)
        n_slots = len(self._slot_infoset)
        slot_count = np.bincount(leaf_slot, minlength=n_slots)
        slot_total = np.bincount(leaf_slot, weights=leaf_value, minlength=n_slots)
        return Depth2Game(
            root_weight=np.full(self.n_roots, 1.0 / self.n_roots),
            n_actions=len(self.our_moves),
            terminal_value=np.array(self._terminal),
            leaf_node=np.array(self._leaf_node, dtype=np.int64),
            leaf_slot=leaf_slot,
            leaf_value=leaf_value,
            slot_infoset=np.array(self._slot_infoset, dtype=np.int64),
            infoset_start=np.array([start for start, _ in self._infosets.values()], dtype=np.int64),
            our_prior=self._our_prior / self.n_roots,
            their_prior=slot_total / np.maximum(slot_count, 1),
        )
