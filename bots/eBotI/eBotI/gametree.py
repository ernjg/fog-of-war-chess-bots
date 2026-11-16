"""A growing imperfect-information game tree over sampled positions.

This is Obscuro's search object (Zhang and Sandholm, arXiv:2506.01242, sections 3 and C):
PCFR+ solves the tree, one-sided GT-CFR grows it, and the Resolve and Maxmargin gadgets sit
above the roots. Nodes are stored in flat arrays (a child is always created after its
parent, so node order is a topological order) and every PCFR+ pass is a handful of numpy
operations per depth layer. Values are from our side, in [-1, 1].

Players: OURS (the bot) and THEIRS (the opponent). A node's ``actor`` is the side to move
there. An expanded node has children and belongs to an infoset; an unexpanded node is a
leaf valued by Stockfish (or the material heuristic); a terminal node has a decided value.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import chess
import numpy as np

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard, fow_moves, observation

from .engine import EnginePool, Job
from .evaluation import evaluate
from .regret import PredictiveRegretMatchingPlus, best_action_strategy
from .rules import side_to_move_wins

OURS, THEIRS = 0, 1
WIN, LOSS = 1.0, -1.0
LEAF_DEPTH = 1           # Stockfish MultiPV depth for the children of an expanded node (C.5)
LEAF_SLICE = (0.02, 0.3)
PUCT_C = 1.0             # C in Q(I, a) (C.4)
NEVER_EXIT = -2.0        # an alternate value below every payoff: the opponent always enters
ROOT_PREV = (-1, -1)     # "no earlier decision of this player on the path"


def _grow(rm: PredictiveRegretMatchingPlus, slot_infoset: np.ndarray, n_infosets: int,
          initial: np.ndarray) -> PredictiveRegretMatchingPlus:
    """``rm`` with new slots appended: regrets at zero, strategy as ``initial``."""
    grown = PredictiveRegretMatchingPlus(
        np.concatenate([rm.slot_infoset, slot_infoset]), n_infosets,
        np.concatenate([rm.strategy, initial]))
    grown.regret[:len(rm.regret)] = rm.regret
    return grown


def _empty_rm() -> PredictiveRegretMatchingPlus:
    return PredictiveRegretMatchingPlus(np.zeros(0, dtype=np.int64), 0, np.zeros(0))


@dataclass
class Expansion:
    """One expansion step's bookkeeping, for the log."""
    expanded: int = 0
    engine_leaves: int = 0
    terminal_hits: int = 0


class GameTree:
    def __init__(self, side: chess.Color, rng: random.Random):
        self.side = side
        self.rng = rng
        # nodes
        self.parent: list[int] = []
        self.move: list[chess.Move | None] = []
        self.depth: list[int] = []
        self.actor: list[int] = []
        self.expanded: list[bool] = []
        self.terminal: list[bool] = []
        self.leaf_value: list[float] = []
        self.infoset: list[int] = []
        self.slot: list[int] = []            # slot (in the parent's actor's slot space) that leads here
        self.first_child: list[int] = []
        self.n_children: list[int] = []
        self.prev: list[tuple[tuple[int, int], tuple[int, int]]] = []  # last (infoset, slot) of each player above
        self.root_J: list[int] = []
        self.root_p: list[float] = []        # p(h | J), unnormalized
        self.boards: dict[int, FowBoard] = {}  # root node -> position
        # infosets
        self.iset_player: list[int] = []
        self.iset_start: list[int] = []
        self.iset_moves: list[tuple[chess.Move, ...]] = []
        self.iset_nodes: list[list[int]] = []
        self.iset_key: dict[tuple, int] = {}
        self.rm = [_empty_rm(), _empty_rm()]
        self.n_slots = [0, 0]
        # PUCT statistics per slot (C.4): visits, and the value samples (two priors, -1 and +1)
        self.visits = [np.zeros(0), np.zeros(0)]
        self.u_count = [np.zeros(0), np.zeros(0)]
        self.u_sum = [np.zeros(0), np.zeros(0)]
        self.u_sq = [np.zeros(0), np.zeros(0)]
        self.iset_visits: list[int] = []
        # the root gadget (B.2, C.1, C.3)
        self.alt: list[float] = []           # alternate value per J, from our side
        self.y_blueprint: list[float] = []   # the opponent's blueprint reach of J (0 for fresh roots)
        self.alpha = np.zeros(0)
        self.resolve = _empty_rm()           # 2 slots per J: enter, exit
        self.maxmargin = _empty_rm()         # one infoset, one slot per J
        self.pmax = 1.0
        self.gadget_ready = False
        # solve state
        self.iterations = 0
        self.root_infoset = -1               # our infoset at the roots that match our view
        self.root_key: tuple | None = None   # that infoset's key; set by the search (set_root_view)
        self.root_obs: str | None = None
        self.root_moves: tuple[chess.Move, ...] = ()
        self.stable: np.ndarray | None = None
        self.track_stability = False
        self._last: dict | None = None       # the last pass, for carry-over and PUCT
        self._cache: dict | None = None

    # ------------------------------------------------------------------ building

    def set_root_view(self, obs: str, our_moves: tuple[chess.Move, ...]) -> None:
        """Name our root infoset: the roots that show us ``obs`` and allow ``our_moves``."""
        self.root_key = (OURS, ROOT_PREV, obs, tuple(m.uci() for m in our_moves))
        self.root_obs, self.root_moves = obs, tuple(our_moves)
        self.root_infoset = self.iset_key.get(self.root_key, -1)

    def new_J(self, alt: float, y_blueprint: float = 0.0) -> int:
        self.alt.append(alt)
        self.y_blueprint.append(y_blueprint)
        self.gadget_ready = False
        return len(self.alt) - 1

    def add_root(self, board: FowBoard, J: int, p: float = 1.0) -> int:
        """A root position, ours to move. Unexpanded until ``expand_nodes`` sees it."""
        node = self._add_node(-1, None, 0, OURS if board.turn == self.side else THEIRS,
                              (ROOT_PREV, ("J", J)), J, p)
        self.boards[node] = board.copy(stack=False)
        return node

    def _add_node(self, parent: int, move: chess.Move | None, depth: int, actor: int,
                  prev, J: int = -1, p: float = 0.0, slot: int = -1) -> int:
        node = len(self.parent)
        self.parent.append(parent)
        self.move.append(move)
        self.depth.append(depth)
        self.actor.append(actor)
        self.expanded.append(False)
        self.terminal.append(False)
        self.leaf_value.append(0.0)
        self.infoset.append(-1)
        self.slot.append(slot)
        self.first_child.append(-1)
        self.n_children.append(0)
        self.prev.append(prev)
        self.root_J.append(J)
        self.root_p.append(p)
        self._cache = None
        return node

    def board_at(self, node: int) -> FowBoard:
        """The position at ``node``, replayed from its root."""
        path = []
        n = node
        while self.parent[n] >= 0:
            path.append(self.move[n])
            n = self.parent[n]
        board = self.boards[n].copy(stack=False)
        for move in reversed(path):
            board.push(move)
        return board

    def finish_gadget(self) -> None:
        """Fix the prior alpha(J) and create the gadget's regret minimizers (C.3, Fig. 9)."""
        m = len(self.alt)
        y = np.array(self.y_blueprint, dtype=float)
        total = y.sum()
        self.alpha = 0.5 * (y / total if total > 0 else np.zeros(m)) + 0.5 / m if m else np.zeros(0)
        if total <= 0:
            self.alpha = np.full(m, 1.0 / m) if m else np.zeros(0)
        enter = np.tile([1.0, 0.0], m)  # start by entering everywhere
        self.resolve = PredictiveRegretMatchingPlus(np.repeat(np.arange(m), 2), m, enter)
        self.maxmargin = PredictiveRegretMatchingPlus(np.zeros(m, dtype=np.int64), 1,
                                                      np.full(m, 1.0 / m) if m else np.zeros(0))
        self.pmax = 1.0
        self.gadget_ready = True
        self._cache = None

    # ------------------------------------------------------------------ expansion

    def expand_nodes(self, nodes: list[int], pool: EnginePool | None, deadline: float,
                     stats: Expansion | None = None) -> None:
        """Add the children of every (unexpanded, non-terminal) node in ``nodes``, valued
        by one depth-LEAF_DEPTH MultiPV call per node (C.5). A node whose side has no move
        becomes terminal: in Fog of War it loses."""
        from .stockfish_search import engine_accepts, engine_fen  # late: that module imports search
        todo = []
        for node in dict.fromkeys(nodes):
            if self.expanded[node] or self.terminal[node]:
                continue
            board = self.board_at(node)
            moves = sorted(fow_moves(board), key=chess.Move.uci)
            if (self.depth[node] == 0 and self.actor[node] == OURS
                    and observation(board, self.side) == self.root_obs):
                # a root of our infoset offers the moves we know we have (the tracker's), which
                # can be fewer than the board allows (castling or en passant we cannot see)
                moves = [m for m in self.root_moves if m in moves]
            if not moves:
                self.terminal[node] = True
                self.leaf_value[node] = LOSS if self.actor[node] == OURS else WIN
                self._cache = None
                continue
            todo.append((node, board, moves))
        if not todo:
            return
        scores: list[dict[str, float] | None] = [None] * len(todo)
        if pool is not None and pool.ready_count() > 0:
            jobs, owners = [], []
            for k, (node, board, _) in enumerate(todo):
                if engine_accepts(board):
                    jobs.append(Job(engine_fen(board), LEAF_DEPTH))
                    owners.append(k)
            if jobs:
                for k, result in zip(owners, pool.run(jobs, deadline, *LEAF_SLICE), strict=True):
                    if result is None or result.no_moves:
                        continue
                    depth = result.complete_depth(list(result.scores))
                    if depth is not None:
                        scores[k] = {uci: found[depth] for uci, found in result.scores.items()
                                     if depth in found}
        for (node, board, moves), table in zip(todo, scores, strict=True):
            self._expand(node, board, moves, table, stats)
        self._cache = None

    def _expand(self, node: int, board: FowBoard, moves: list[chess.Move],
                table: dict[str, float] | None, stats: Expansion | None) -> None:
        actor = self.actor[node]
        sign = 1.0 if actor == OURS else -1.0  # Stockfish scores for the side to move
        first = len(self.parent)
        values = np.zeros(len(moves))
        prev_ours, prev_theirs = self.prev[node]
        infoset = self._infoset_for(node, board, moves)
        start = self.iset_start[infoset]
        for k, move in enumerate(moves):
            board.push(move)
            child_actor = OURS if board.turn == self.side else THEIRS
            if actor == OURS:
                prev = ((infoset, start + k), prev_theirs)
            else:
                prev = (prev_ours, (infoset, start + k))
            child = self._add_node(node, move, self.depth[node] + 1, child_actor, prev, slot=start + k)
            if side_to_move_wins(board):          # the mover left a king en prise: the side to move takes it
                self.terminal[child] = True
                value = WIN if child_actor == OURS else LOSS
            elif table is not None and move.uci() in table:
                value = sign * table[move.uci()]
                if stats is not None:
                    stats.engine_leaves += 1
            else:
                value = evaluate(board, self.side)
            board.pop()
            self.leaf_value[child] = value
            values[k] = value
        self.first_child[node] = first
        self.n_children[node] = len(moves)
        self.expanded[node] = True
        self.infoset[node] = infoset
        self.iset_nodes[infoset].append(node)
        if stats is not None:
            stats.expanded += 1
        if len(self.iset_nodes[infoset]) == 1:
            # a new infoset starts on the child Stockfish likes best (C.5)
            own = values if actor == OURS else -values
            initial = best_action_strategy(own, np.array([0]))
            self.rm[actor] = _grow(self.rm[actor], np.full(len(moves), infoset, dtype=np.int64),
                                   len(self.iset_player), initial)
            for name in ("visits", "u_count", "u_sum", "u_sq"):
                arrays = getattr(self, name)
                fill = {"visits": 0.0, "u_count": 2.0, "u_sum": 0.0, "u_sq": 2.0}[name]
                arrays[actor] = np.concatenate([arrays[actor], np.full(len(moves), fill)])
            self.n_slots[actor] += len(moves)

    def _infoset_for(self, node: int, board: FowBoard, moves: list[chess.Move]) -> int:
        actor = self.actor[node]
        color = self.side if actor == OURS else not self.side
        prev = self.prev[node][actor]
        key = (actor, prev, observation(board, color), tuple(m.uci() for m in moves))
        found = self.iset_key.get(key)
        if found is None:
            found = len(self.iset_player)
            self.iset_key[key] = found
            if key == self.root_key:
                self.root_infoset = found
            self.iset_player.append(actor)
            self.iset_start.append(self.n_slots[actor])
            self.iset_moves.append(tuple(moves))
            self.iset_nodes.append([])
            self.iset_visits.append(0)
        else:
            assert self.iset_moves[found] == tuple(moves)
        return found

    def choose_leaves(self, count: int, exploring: int) -> list[int]:
        """Leaves to expand, each found by one walk from the root under the profile of
        one-sided GT-CFR (3.3, C.4): the exploring player plays half uniform-over-support,
        half PUCT; the other plays its current strategy."""
        if not self.gadget_ready or self._last is None:
            roots = [n for n in range(len(self.parent)) if self.parent[n] < 0]
            return [n for n in roots if not self.expanded[n] and not self.terminal[n]][:count]
        leaves = []
        for _ in range(count * 3):
            if len(leaves) >= count:
                break
            node = self._walk(exploring)
            if node is not None and node not in leaves:
                leaves.append(node)
        return leaves

    def _walk(self, exploring: int) -> int | None:
        last = self._last
        piJ = last["piJ"]
        total = piJ.sum()
        probs = piJ / total if total > 0 else np.full(len(piJ), 1.0 / max(len(piJ), 1))
        J = self.rng.choices(range(len(probs)), probs)[0]
        roots = last["roots_of_J"][J]
        weights = [self.root_p[n] for n in roots]
        node = self.rng.choices(roots, weights)[0] if sum(weights) > 0 else self.rng.choice(roots)
        while self.expanded[node]:
            actor = self.actor[node]
            infoset = self.infoset[node]
            start, n = self.iset_start[infoset], self.n_children[node]
            strategy = self.rm[actor].strategy[start:start + n]
            if actor == exploring:
                support = strategy > 0
                uniform = support / support.sum() if support.any() else np.full(n, 1.0 / n)
                q = self._puct(actor, infoset, start, n)
                probs = 0.5 * uniform
                probs[int(np.argmax(q))] += 0.5
                self.iset_visits[infoset] += 1
            else:
                probs = strategy if strategy.sum() > 0 else np.full(n, 1.0 / n)
            a = self.rng.choices(range(n), probs)[0]
            if actor == exploring:
                self.visits[actor][start + a] += 1
            node = self.first_child[node] + a
        return None if self.terminal[node] else node

    def _puct(self, actor: int, infoset: int, start: int, n: int) -> np.ndarray:
        """Q(I, a) = u(x, y | I, a) + C sigma(I, a) sqrt(N(I)) / (1 + N(I, a))  (C.4)."""
        last = self._last
        u = last["u"][actor][start:start + n]
        self.u_count[actor][start:start + n] += 1
        self.u_sum[actor][start:start + n] += u
        self.u_sq[actor][start:start + n] += u * u
        count = self.u_count[actor][start:start + n]
        mean = self.u_sum[actor][start:start + n] / count
        var = np.maximum(self.u_sq[actor][start:start + n] / count - mean * mean, 0.0)
        return u + PUCT_C * np.sqrt(var) * np.sqrt(self.iset_visits[infoset]) / (1.0 + self.visits[actor][start:start + n])

    # ------------------------------------------------------------------ solving

    def _arrays(self) -> dict:
        if self._cache is None:
            depth = np.array(self.depth, dtype=np.int64)
            layers = [np.flatnonzero(depth == d) for d in range(int(depth.max()) + 1 if len(depth) else 0)]
            roots = layers[0] if layers else np.zeros(0, dtype=np.int64)
            root_J = np.array([self.root_J[n] for n in roots], dtype=np.int64)
            root_p = np.array([self.root_p[n] for n in roots], dtype=float)
            m = len(self.alt)
            p_total = np.bincount(root_J, weights=root_p, minlength=m) if m else np.zeros(0)
            p_norm = root_p / np.where(p_total[root_J] > 0, p_total[root_J], 1.0) if m else root_p
            roots_of_J = [[] for _ in range(m)]
            for n, J in zip(roots.tolist(), root_J.tolist()):
                roots_of_J[J].append(n)
            self._cache = dict(
                parent=np.array(self.parent, dtype=np.int64), depth=depth, layers=layers,
                actor=np.array(self.actor, dtype=np.int64), expanded=np.array(self.expanded, dtype=bool),
                leaf_value=np.array(self.leaf_value, dtype=float), slot=np.array(self.slot, dtype=np.int64),
                infoset=np.array(self.infoset, dtype=np.int64), roots=roots, root_J=root_J,
                p_norm=p_norm, roots_of_J=roots_of_J, alt=np.array(self.alt, dtype=float))
        return self._cache

    def _gadget_weights(self) -> tuple[np.ndarray, np.ndarray]:
        """(pi_opp(J), f(J)): the opponent's blended root probability of J (Fig. 10, line 12),
        and the factor everyone but the opponent contributes at J."""
        m = len(self.alt)
        if m == 0:
            return np.zeros(0), np.zeros(0)
        enter = self.resolve.strategy[0::2]
        select = self.maxmargin.strategy
        piJ = self.pmax * self.alpha * enter + (1.0 - self.pmax) * select
        fJ = self.pmax * self.alpha + (1.0 - self.pmax)
        return piJ, fJ

    def _pass(self, A: dict) -> dict:
        N = len(A["parent"])
        x, y = self.rm[OURS].strategy, self.rm[THEIRS].strategy
        piJ, fJ = self._gadget_weights()
        reach_x = np.ones(N)
        reach_y = np.ones(N)
        f_ours = np.zeros(N)    # what everyone but us contributes from the gadget: pi_opp(J) p(h|J)
        f_theirs = np.zeros(N)  # what everyone but the opponent contributes: f(J) p(h|J)
        roots = A["roots"]
        f_ours[roots] = piJ[A["root_J"]] * A["p_norm"]
        f_theirs[roots] = fJ[A["root_J"]] * A["p_norm"]
        parent, slot, actor = A["parent"], A["slot"], A["actor"]
        for layer in A["layers"][1:]:
            p = parent[layer]
            s = slot[layer]
            ours_acts = actor[p] == OURS
            reach_x[layer] = reach_x[p] * np.where(ours_acts, x[np.where(ours_acts, s, 0)] if len(x) else 1.0, 1.0)
            reach_y[layer] = reach_y[p] * np.where(ours_acts, 1.0, y[np.where(ours_acts, 0, s)] if len(y) else 1.0)
            f_ours[layer] = f_ours[p]
            f_theirs[layer] = f_theirs[p]
        val = A["leaf_value"].copy()
        expanded = A["expanded"]
        for d in range(len(A["layers"]) - 1, 0, -1):
            layer = A["layers"][d]
            p = parent[layer]
            s = slot[layer]
            ours_acts = actor[p] == OURS
            prob = np.where(ours_acts, x[np.where(ours_acts, s, 0)] if len(x) else 0.0,
                            y[np.where(ours_acts, 0, s)] if len(y) else 0.0)
            total = np.bincount(p, weights=prob * val[layer], minlength=N)
            targets = A["layers"][d - 1]
            targets = targets[expanded[targets]]
            val[targets] = total[targets]
        return dict(reach_x=reach_x, reach_y=reach_y, f_ours=f_ours, f_theirs=f_theirs, val=val,
                    piJ=piJ, fJ=fJ, roots_of_J=A["roots_of_J"])

    def _counterfactual(self, A: dict, R: dict, player: int) -> tuple[np.ndarray, np.ndarray]:
        """(cf value per slot, cf reach per infoset) of ``player``: for every child of a node
        where the player acts, the child's value weighted by everyone else's reach."""
        parent, slot, actor = A["parent"], A["slot"], A["actor"]
        children = np.flatnonzero((parent >= 0))
        children = children[actor[parent[children]] == player]
        p = parent[children]
        other_reach = R["reach_y"] if player == OURS else R["reach_x"]
        factor = R["f_ours"] if player == OURS else R["f_theirs"]
        weight = factor[p] * other_reach[p]
        sign = 1.0 if player == OURS else -1.0
        cfv = np.bincount(slot[children], weights=weight * sign * R["val"][children],
                          minlength=self.n_slots[player])
        acting = np.flatnonzero(A["expanded"] & (actor == player))
        cfreach = np.bincount(A["infoset"][acting], weights=factor[acting] * other_reach[acting],
                              minlength=len(self.iset_player))
        return cfv, cfreach

    def iterate(self) -> None:
        """One PCFR+ iteration: ours, then theirs (alternating), then the gadget (Fig. 10)."""
        if not self.gadget_ready:
            self.finish_gadget()
        A = self._arrays()
        R = self._pass(A)
        u = [None, None]
        if self.n_slots[OURS]:
            cfv, cfreach = self._counterfactual(A, R, OURS)
            self.rm[OURS].update(cfv)
            u[OURS] = cfv / np.where(cfreach > 0, cfreach, 1.0)[self.rm[OURS].slot_infoset]
            R = self._pass(A)
        if self.n_slots[THEIRS]:
            cfv, cfreach = self._counterfactual(A, R, THEIRS)
            self.rm[THEIRS].update(cfv)
            u[THEIRS] = cfv / np.where(cfreach > 0, cfreach, 1.0)[self.rm[THEIRS].slot_infoset]
        # the gadget: V(J) under the current strategies, then RM+ at every J (Fig. 10, lines 5-12)
        m = len(self.alt)
        if m:
            V = np.bincount(A["root_J"], weights=A["p_norm"] * R["val"][A["roots"]], minlength=m)
            alt = A["alt"]
            self.resolve.update(np.stack([-V, -alt], axis=1).ravel())      # enter, exit (opponent's view)
            self.maxmargin.update(alt - V)                                  # pick the J with the smallest margin
            self.pmax = float(self.resolve.strategy[0::2].max())
            R["V"] = V
        for player in (OURS, THEIRS):
            if u[player] is None:
                u[player] = np.zeros(self.n_slots[player])
        R["u"] = u
        self._last = R
        self.iterations += 1
        if self.track_stability and self.root_infoset >= 0:
            start = self.iset_start[self.root_infoset]
            n = len(self.iset_moves[self.root_infoset])
            now = self.rm[OURS].strategy[start:start + n] > 0
            self.stable = now if self.stable is None else (self.stable & now)

    # ------------------------------------------------------------------ reading the result

    def root_strategy(self) -> np.ndarray:
        start = self.iset_start[self.root_infoset]
        n = len(self.iset_moves[self.root_infoset])
        return self.rm[OURS].strategy[start:start + n].copy()

    def root_action_values(self) -> np.ndarray:
        start = self.iset_start[self.root_infoset]
        n = len(self.iset_moves[self.root_infoset])
        if self._last is None:
            return np.zeros(n)
        return self._last["u"][OURS][start:start + n]

    def value(self) -> float:
        """Our expected value, with the roots weighted as the opponent's gadget enters them."""
        if self._last is None or "V" not in self._last:
            return 0.0
        piJ = self._last["piJ"]
        total = piJ.sum()
        if total <= 0:
            return float(self._last["V"].mean())
        return float(piJ @ self._last["V"] / total)

    def margins(self) -> np.ndarray:
        """V(J) - alt(J): nonnegative everywhere means the current strategy is safe."""
        if self._last is None or "V" not in self._last:
            return np.zeros(0)
        return self._last["V"] - np.array(self.alt)

    @property
    def n_nodes(self) -> int:
        return len(self.parent)

    @property
    def n_infosets(self) -> int:
        return len(self.iset_player)

    # ------------------------------------------------------------------ carry-over (Fig. 9)

    def carry_over(self, played: chess.Move, obs: str, our_moves: tuple[chess.Move, ...],
                   max_kluss: int, max_roots: int = 256) -> "GameTree":
        """The subgame for the next turn, from this tree: the nodes two plies below the roots
        (our move ``played``, then a reply) become the new roots. Those that show us ``obs``
        are our new infoset; those the opponent cannot tell apart from them (same view and
        history for it) are the KLUSS roots. Every new root J gets the alternate value
        u(x, y | J) - gift(J) (C.2) and its blueprint reach y(J) (C.3)."""
        new = GameTree(self.side, self.rng)
        new.set_root_view(obs, our_moves)
        if self._last is None or self.root_infoset < 0:
            return new
        R = self._last
        x = self.rm[OURS].strategy
        y = self.rm[THEIRS].strategy
        root_start = self.iset_start[self.root_infoset]
        root_moves = self.iset_moves[self.root_infoset]
        if played not in root_moves:
            return new
        slot_a = root_start + root_moves.index(played)
        u_theirs = R["u"][THEIRS]
        # candidate roots: depth-2 nodes under a root of our infoset I
        candidates: dict[tuple, list[int]] = {}   # J key -> nodes
        node_info: dict[int, tuple[bool, float, float, float]] = {}
        for root in self.iset_nodes[self.root_infoset]:
            if not self.expanded[root]:
                continue
            for a in range(self.n_children[root]):
                child = self.first_child[root] + a   # the opponent's node after our move a
                if not self.expanded[child] or self.terminal[child]:
                    continue
                x_a = float(x[root_start + a])
                if x_a <= 0 and child != self.first_child[root] + root_moves.index(played):
                    continue
                J_old = self.infoset[child]
                for b in range(self.n_children[child]):
                    grand = self.first_child[child] + b   # our node after the reply b
                    if self.terminal[grand]:
                        continue
                    board = self.board_at(grand)
                    in_I = observation(board, self.side) == obs and self.move[child] == played
                    if in_I and not set(our_moves) <= set(fow_moves(board)):
                        continue
                    if in_I and self.expanded[grand] and self.iset_moves[self.infoset[grand]] != our_moves:
                        continue  # expanded with moves we do not offer now: not one of ours
                    key = (J_old, b, observation(board, not self.side))
                    weight = float(R["f_theirs"][root] * (1.0 if self.move[child] == played else x_a))
                    if weight <= 0:
                        continue
                    candidates.setdefault(key, []).append(grand)
                    slot_b = self.iset_start[J_old] + b
                    y_b = float(y[slot_b])
                    node_info[grand] = (in_I, weight, y_b, slot_b)
        # the heaviest of our nodes, up to max_roots; every J that holds one comes along,
        # and KLUSS nodes come with their J, capped
        ranked = sorted((n for n, info in node_info.items() if info[0]), key=lambda n: -node_info[n][1])
        allowed = set(ranked[:max_roots])
        kluss_budget = max_kluss
        chosen: list[tuple[int, int, float, float, float]] = []  # (node, Jnew, p, alt contribution...)
        for key, nodes in candidates.items():
            ours_here = [n for n in nodes if node_info[n][0] and n in allowed]
            if not ours_here:
                continue
            others = [n for n in nodes if not node_info[n][0]]
            others.sort(key=lambda n: -node_info[n][1])
            keep = ours_here + others[:kluss_budget]
            kluss_budget -= len(others[:kluss_budget])
            weights = np.array([node_info[n][1] for n in keep])
            values = np.array([R["val"][n] for n in keep])
            u_J = float(weights @ values / weights.sum())
            J_old, b, _ = key
            slot_b = node_info[keep[0]][3]
            start = self.iset_start[J_old]
            n_b = len(self.iset_moves[J_old])
            u_Jold = float(y[start:start + n_b] @ (-u_theirs[start:start + n_b]))  # our value at J_old
            gift = max(0.0, u_Jold - (-float(u_theirs[slot_b])))
            y_J = node_info[keep[0]][2]
            Jnew = new.new_J(u_J - gift, y_J)
            for n in keep:
                chosen.append((n, Jnew, node_info[n][1]))
        if not chosen:
            return new
        # copy the chosen nodes and their descendants
        self._copy_subtrees(new, [n for n, _, _ in chosen], {n: (J, p) for n, J, p in chosen})
        return new

    def _copy_subtrees(self, new: "GameTree", roots: list[int], root_J_p: dict[int, tuple[int, float]]) -> None:
        mapping: dict[int, int] = {}
        order: list[int] = []
        stack = list(roots)
        keep = set(roots)
        while stack:
            n = stack.pop()
            order.append(n)
            if self.expanded[n]:
                for c in range(self.first_child[n], self.first_child[n] + self.n_children[n]):
                    keep.add(c)
                    stack.append(c)
        order.sort()
        iset_map: dict[int, int] = {}
        for n in order:
            is_root = n in root_J_p
            parent = -1 if is_root else mapping[self.parent[n]]
            depth = 0 if is_root else new.depth[parent] + 1
            J, p = root_J_p.get(n, (-1, 0.0))
            node = new._add_node(parent, None if is_root else self.move[n], depth, self.actor[n],
                                 (ROOT_PREV, ("J", J)) if is_root else (ROOT_PREV, ROOT_PREV), J, p)
            mapping[n] = node
            if is_root:
                new.boards[node] = self.board_at(n)
            new.terminal[node] = self.terminal[n]
            new.leaf_value[node] = self.leaf_value[n]
        # infosets of the copied expanded nodes, in copy order so parents come first
        for n in order:
            if not self.expanded[n]:
                continue
            node = mapping[n]
            old_iset = self.infoset[n]
            actor = self.actor[n]
            prev = new.prev[node]
            if old_iset not in iset_map:
                moves = self.iset_moves[old_iset]
                start_old = self.iset_start[old_iset]
                n_a = len(moves)
                new_iset = len(new.iset_player)
                iset_map[old_iset] = new_iset
                new.iset_player.append(actor)
                new.iset_start.append(new.n_slots[actor])
                new.iset_moves.append(moves)
                new.iset_nodes.append([])
                new.iset_visits.append(0)
                new.rm[actor] = _grow(new.rm[actor], np.full(n_a, new_iset, dtype=np.int64),
                                      new_iset + 1, self.rm[actor].strategy[start_old:start_old + n_a])
                new.rm[actor].regret[-n_a:] = self.rm[actor].regret[start_old:start_old + n_a]
                for name in ("visits", "u_count", "u_sum", "u_sq"):
                    arrays = getattr(new, name)
                    arrays[actor] = np.concatenate([arrays[actor], getattr(self, name)[actor][start_old:start_old + n_a]])
                new.n_slots[actor] += n_a
                # the key, in the new tree's chain of decisions
                board = new.board_at(node)
                color = self.side if actor == OURS else not self.side
                key = (actor, prev[actor], observation(board, color), tuple(m.uci() for m in moves))
                new.iset_key[key] = new_iset
                if key == new.root_key:
                    new.root_infoset = new_iset
            new_iset = iset_map[old_iset]
            new.infoset[node] = new_iset
            new.expanded[node] = True
            new.iset_nodes[new_iset].append(node)
            start = new.iset_start[new_iset]
            first = mapping[self.first_child[n]]
            new.first_child[node] = first
            new.n_children[node] = self.n_children[n]
            for k in range(self.n_children[n]):
                child = first + k
                new.slot[child] = start + k
                if actor == OURS:
                    new.prev[child] = ((new_iset, start + k), prev[THEIRS])
                else:
                    new.prev[child] = (prev[OURS], (new_iset, start + k))
        new._cache = None
