"""One move of Obscuro's search (Zhang and Sandholm, Fig. 8 and 9): build the subgame
from the previous tree and fresh positions, solve and grow it until the budget ends, then
pick the move with purification. The tree and value are kept for the next turn."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

import chess
import numpy as np

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard, fow_moves

from .belief import state_key
from .engine import EnginePool
from .gametree import NEVER_EXIT, OURS, Expansion, GameTree
from .rules import side_to_move_wins
from .search import choose_action
from .stockfish_search import ATTACKED_WEIGHT, SCAN_STATES, classify

MIN_INFOSET_SIZE = 256   # roots added from the belief until this many (MinInfosetSize, Fig. 9)
MAX_KLUSS = 128          # positions the opponent confuses with ours, carried from the old tree
MAX_SUPPORT = 3          # moves mixed between when the strategy is safe (C.8)
FILL_SHARE = 0.6         # of the expansion time, at most, for adding and expanding roots: at our
                         # node rate the roots decide the move, expansions refine it
MIX_MARGIN = 0.02        # a stable move may be mixed in if its value is within this of the best
EXPAND_SHARE = 0.8       # of the budget: tree growth stops here, pure solving follows (3.4)
BATCH = 16               # leaves expanded between two solving spells
RESERVE = 0.08           # seconds kept back at the end of the budget


@dataclass(frozen=True)
class ObscuroResult:
    move: chess.Move
    value: float
    roots: int
    carried: int
    kluss: int
    nodes: int
    infosets: int
    expansions: int
    engine_leaves: int
    iterations: int
    pmax: float
    mixed: int            # moves the final strategy was sampled from
    repeat_avoided: bool
    strategy: tuple[float, ...]
    risk: float           # share of scanned positions in which the move loses the king
    scanned: int


class ObscuroSearch:
    def __init__(self, side: chess.Color, rng: random.Random, leaf_depth: int | None = None,
                 root_depth: int | None = None, perfect_opponent: bool = False):
        self.side = side
        self.rng = rng
        self.perfect_opponent = perfect_opponent
        self.leaf_depth = leaf_depth
        self.root_depth = root_depth
        self.tree: GameTree | None = None
        self.v_star: float | None = None
        self.played: chess.Move | None = None

    def forget(self) -> None:
        """Drop the carried tree (we played a move the search did not choose)."""
        self.tree = None
        self.v_star = None
        self.played = None

    def record(self, move: chess.Move) -> None:
        if self.tree is not None and self.played is not None and move != self.played:
            self.forget()
        self.played = move

    def search(self, states: list[FowBoard], our_moves: list[chess.Move], obs: str,
               budget: float, pool: EnginePool | None,
               repeat_counts: list[int] | None = None) -> ObscuroResult | None:
        start = time.monotonic()
        deadline = start + budget - RESERVE
        expand_until = start + EXPAND_SHARE * (budget - RESERVE)
        moves = tuple(sorted(our_moves, key=chess.Move.uci))
        stats = Expansion()

        # 1. the subgame: carried roots first, then fresh positions (Fig. 9)
        carried = kluss = 0
        fill_until = start + FILL_SHARE * (expand_until - start)
        if self.tree is not None and self.played is not None:
            tree = self.tree.carry_over(self.played, obs, moves, MAX_KLUSS, MIN_INFOSET_SIZE)
            if not tree.boards:
                tree = GameTree(self.side, self.rng)
                tree.set_root_view(obs, moves)
            else:
                # roots that were leaves of the old tree get their children now
                pending = [n for n in tree.boards if not tree.expanded[n] and not tree.terminal[n]]
                tree.expand_nodes(pending, pool, min(fill_until, deadline), stats)
                carried = len(tree.iset_nodes[tree.root_infoset]) if tree.root_infoset >= 0 else 0
                kluss = len(tree.boards) - carried
        else:
            tree = GameTree(self.side, self.rng)
            tree.set_root_view(obs, moves)
        tree.perfect_opponent = self.perfect_opponent
        if self.leaf_depth:
            tree.leaf_depth = self.leaf_depth
        if self.root_depth:
            tree.root_depth = self.root_depth
        have = {state_key(tree.boards[n]) for n in tree.boards}
        fresh: list[int] = []
        wanted = min(len(states), MIN_INFOSET_SIZE)
        order = list(range(len(states)))
        self.rng.shuffle(order)
        for index in order:
            if carried + len(fresh) >= wanted or time.monotonic() > fill_until:
                break
            board = states[index]
            if board.turn != self.side or state_key(board) in have:
                continue
            if not set(moves) <= set(fow_moves(board)):
                continue
            have.add(state_key(board))
            king = board.king(self.side)
            attacked = king is not None and board.is_attacked_by(not self.side, king)
            J = tree.new_J(NEVER_EXIT, weight=ATTACKED_WEIGHT if attacked else 1.0)  # alt fixed below
            fresh.append(tree.add_root(board, J, 1.0))
            if len(fresh) % BATCH == 0:
                tree.expand_nodes(fresh[-BATCH:], pool, min(fill_until, deadline), stats)
        if fresh:
            tree.expand_nodes(fresh, pool, min(fill_until + 0.2, deadline), stats)
        if tree.root_infoset < 0:
            return None
        for node in fresh:                   # alternate value min{v~(h), v*} (Fig. 9, line 14)
            if tree.expanded[node] and self.v_star is not None:
                first, n = tree.first_child[node], tree.n_children[node]
                v_tilde = max(tree.leaf_value[first:first + n]) if n else 0.0
                tree.alt[tree.root_J[node]] = min(v_tilde, self.v_star)
        tree.finish_gadget()
        tree.iterate()

        # 2. grow and solve until the budget ends (3.4): a batch of expansions, then as much
        #    solving as the batch took; after EXPAND_SHARE, solving only
        exploring = OURS
        half = start + budget / 2
        while time.monotonic() < expand_until:
            batch_start = time.monotonic()
            leaves = tree.choose_leaves(BATCH, exploring)
            exploring ^= 1
            if leaves:
                tree.expand_nodes(leaves, pool, min(batch_start + 0.5, expand_until), stats)
            else:
                stats.terminal_hits += 1
            spent = time.monotonic() - batch_start
            solve_until = min(time.monotonic() + max(spent, 0.005), expand_until)
            while True:
                if not tree.track_stability and time.monotonic() >= half:
                    tree.track_stability = True
                tree.iterate()
                if time.monotonic() >= solve_until:
                    break
        while time.monotonic() < deadline:
            if not tree.track_stability and time.monotonic() >= half:
                tree.track_stability = True
            tree.iterate()

        # 3. the move (Fig. 8, C.8), with v4's king-safety check on top: the share of a wide
        #    sample of positions in which a move loses the king at once, which the sampled
        #    roots alone can miss
        strategy = tree.root_strategy()
        values = tree.root_action_values()
        risk, scanned = self._risk(states, moves)
        final_values = -risk + (1.0 - risk) * values
        top = int(np.argmax(final_values))
        play = np.zeros_like(strategy)
        play[top] = 1.0
        mixed = 1
        if tree.pmax <= 0.0 and tree.stable is not None:   # Maxmargin: safe, so mixing is allowed
            allowed = tree.stable & (final_values >= final_values[top] - MIX_MARGIN) & (strategy > 0)
            allowed[top] = True
            if allowed.sum() > MAX_SUPPORT:
                ranked = np.argsort(-strategy)
                keep = np.zeros_like(allowed)
                keep[[i for i in ranked if allowed[i]][:MAX_SUPPORT]] = True
                allowed = keep
            play = np.where(allowed, strategy, 0.0)
            play[top] += strategy[~allowed].sum()
            if play.sum() <= 0:
                play[top] = 1.0
            mixed = int((play > 0).sum())
        chosen = self.rng.choices(range(len(moves)), play)[0] if mixed > 1 else top
        counts = None if repeat_counts is None else np.asarray(
            [repeat_counts[our_moves.index(m)] for m in moves], dtype=float)
        pick = np.zeros_like(play)
        pick[chosen] = 1.0
        final = choose_action(pick, final_values, float(final_values[chosen]), counts)

        self.tree = tree
        self.v_star = tree.value()
        self.played = moves[final]
        return ObscuroResult(moves[final], float(final_values[final]), len(tree.boards), carried, kluss,
                             tree.n_nodes, tree.n_infosets, stats.expanded, stats.engine_leaves,
                             tree.iterations, tree.pmax, mixed, final != chosen,
                             tuple(float(v) for v in strategy), float(risk[final]), scanned)

    def _risk(self, states: list[FowBoard], moves: tuple[chess.Move, ...]) -> tuple[np.ndarray, int]:
        """Per move, the weighted share of up to SCAN_STATES positions in which it loses the
        king at once; positions with our king attacked count ATTACKED_WEIGHT times (as v4)."""
        order = list(range(len(states)))
        self.rng.shuffle(order)
        total = 0.0
        suicide = np.zeros(len(moves))
        scanned = 0
        for index in order[:SCAN_STATES]:
            board = states[index]
            if board.turn != self.side:
                continue
            classes = classify(board, moves)
            if classes is None:
                continue
            king = board.king(self.side)
            weight = ATTACKED_WEIGHT if king is not None and board.is_attacked_by(not self.side, king) else 1.0
            total += weight
            suicide[list(classes.suicide)] += weight
            scanned += 1
        return (suicide / total if total > 0 else suicide), scanned
