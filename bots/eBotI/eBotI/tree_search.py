"""Obscuro's search with the tree kept in the C++ helper (tree.inc): the same pipeline as
obscuro_search.py, but the helper grows and solves the tree while Python only decides the
time, asks Stockfish for leaf values, and picks the move (Fig. 8 and 9 of the paper)."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

import chess
import numpy as np

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard

from .engine import EnginePool, Job
from .position_set import Helper, HelperError, HelperRefused
from .search import choose_action
from .stockfish_search import ATTACKED_WEIGHT, engine_accepts, engine_fen, suicide_share

MIN_INFOSET_SIZE = 256   # roots added from the belief until this many (MinInfosetSize, Fig. 9)
MAX_KLUSS = 128
MAX_SUPPORT = 3
MIX_MARGIN = 0.02
FILL_SHARE = 0.4         # of the growing time, at most, for valuing the roots
EXPAND_SHARE = 0.75      # of the budget: growth stops here, pure solving follows
SOLVE_RATIO = 2.0        # solving time between two batches, as a multiple of the batch's time
BATCH = 128              # leaves per round trip to the helper
LEAF_DEPTH = 1           # the paper's leaf depth; the tree itself supplies the lookahead now
ROOT_DEPTH = 1
LEAF_SLICE = (0.002, 0.5)
RESERVE = 0.08
ANSWER_SECONDS = 5.0


@dataclass(frozen=True)
class TreeResult:
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
    mixed: int
    repeat_avoided: bool
    risk: float
    scanned: int
    depth: int = 0
    leaf_depth: float = 0.0


class TreeSearch:
    """One instance per game; the helper keeps the tree between turns."""

    def __init__(self, side: chess.Color, rng: random.Random, leaf_depth: int = LEAF_DEPTH,
                 root_depth: int = ROOT_DEPTH):
        self.side = side
        self.rng = rng
        self.leaf_depth = leaf_depth
        self.root_depth = root_depth
        self.played: chess.Move | None = None
        self.have_tree = False
        self.v_star: float | None = None
        self.engines: int | None = None   # engines started inside the helper (None: not asked yet)

    def forget(self) -> None:
        self.have_tree = False
        self.played = None
        self.v_star = None

    def record(self, move: chess.Move) -> None:
        if self.have_tree and self.played is not None and move != self.played:
            self.forget()
        self.played = move

    def search(self, helper: Helper, states: list[FowBoard], our_moves: list[chess.Move], obs: str,
               budget: float, pool: EnginePool | None, repeat_counts: list[int] | None = None,
               uniform_states: list[FowBoard] | None = None, engine_path: str | None = None,
               engine_count: int = 2, hash_mb: int = 64) -> TreeResult | None:
        start = time.monotonic()
        if self.engines is None:
            self.engines = 0
            if engine_path:
                header = self._ask(helper, f"tree engines {engine_count} {hash_mb} {engine_path}")
                self.engines = int(header.split("ready=")[1])
        in_helper = self.engines > 0
        deadline = start + budget - RESERVE
        expand_until = start + EXPAND_SHARE * (budget - RESERVE)
        moves = tuple(sorted(our_moves, key=chess.Move.uci))
        color = "w" if self.side else "b"
        played = self.played.uci() if (self.have_tree and self.played is not None) else "-"
        ucis = " ".join(m.uci() for m in moves)
        self._ask(helper, f"tree start {color} {obs} {len(moves)} {ucis} {played} {MIN_INFOSET_SIZE} "
                          f"{MAX_KLUSS} {self.rng.randrange(1 << 30)}")
        v_star = "none" if self.v_star is None else f"{self.v_star:.6f}"
        self._ask(helper, f"tree fill {MIN_INFOSET_SIZE} {int(ATTACKED_WEIGHT * 100)} {v_star}")
        expansions = engine_leaves = 0

        # 1. value the roots (and any carried leaf that is now a root)
        fill_until = start + FILL_SHARE * (expand_until - start)
        while time.monotonic() < fill_until:
            e, l = self._grow(helper, pool, in_helper, 0, self.root_depth, min(fill_until + 0.2, deadline))
            if not e:
                break
            expansions += e
            engine_leaves += l
        self._ask(helper, "tree gadget")
        try:
            self._ask(helper, "tree solve 1 0")
        except HelperRefused:   # no root fits our view: nothing to search
            return None

        # 2. grow and solve in turns until the growth share ends, then solve only
        exploring = 0
        half = start + budget / 2
        while time.monotonic() < expand_until:
            batch_start = time.monotonic()
            e, l = self._grow(helper, pool, in_helper, exploring, self.leaf_depth, min(batch_start + 0.5, expand_until))
            exploring ^= 1
            expansions += e
            engine_leaves += l
            spent = time.monotonic() - batch_start
            solve_ms = max(spent, 0.003) * 1000 * SOLVE_RATIO
            self._ask(helper, f"tree solve {solve_ms:.1f} {int(time.monotonic() >= half)}")
        left = deadline - time.monotonic()
        if left > 0.005:
            self._ask(helper, f"tree solve {left * 1000:.1f} 1")

        # 3. the move
        header, rows = helper.ask("tree result", time.monotonic() + ANSWER_SECONDS)
        fields = dict(word.split("=") for word in header.split()[2:])
        order, strategy, values, stable = [], [], [], []
        for row in rows:
            _, uci, prob, value, is_stable = row.split()
            order.append(chess.Move.from_uci(uci))
            strategy.append(float(prob))
            values.append(float(value))
            stable.append(is_stable == "1")
        if not order:
            return None
        strategy, values, stable = np.array(strategy), np.array(values), np.array(stable)
        risk = suicide_share(uniform_states or states, order)
        if risk is None:
            risk = np.zeros(len(order))
        final_values = -risk + (1.0 - risk) * values
        top = int(np.argmax(final_values))
        pmax = float(fields["pmax"])
        play = np.zeros_like(strategy)
        play[top] = 1.0
        mixed = 1
        if pmax <= 0.0:
            allowed = stable & (final_values >= final_values[top] - MIX_MARGIN) & (strategy > 0)
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
        chosen = self.rng.choices(range(len(order)), play)[0] if mixed > 1 else top
        counts = None if repeat_counts is None else np.asarray(
            [repeat_counts[our_moves.index(m)] for m in order], dtype=float)
        pick = np.zeros_like(play)
        pick[chosen] = 1.0
        final = choose_action(pick, final_values, float(final_values[chosen]), counts)
        self.have_tree = True
        self.v_star = float(fields["value"])
        self.played = order[final]
        return TreeResult(order[final], float(final_values[final]), int(fields["roots"]),
                          int(fields["carried"]), int(fields["kluss"]), int(fields["nodes"]),
                          int(fields["infosets"]), expansions, engine_leaves, int(fields["iters"]),
                          pmax, mixed, final != chosen, float(risk[final]),
                          len(uniform_states or states), int(fields.get("depth", 0)),
                          float(fields.get("leaf_depth", 0)))

    # ------------------------------------------------------------------ helper round trips

    def _ask(self, helper: Helper, text: str) -> str:
        header, _ = helper.ask(text, time.monotonic() + ANSWER_SECONDS)
        return header

    def _grow(self, helper: Helper, pool: EnginePool | None, in_helper: bool, exploring: int,
              depth: int, deadline: float) -> tuple[int, int]:
        """One batch of expansions: inside the helper when it has engines, else through
        Python's pool. Returns (expanded, engine-valued leaves)."""
        if in_helper:
            ms = max((deadline - time.monotonic()) * 1000, 1.0)
            header = self._ask(helper, f"tree grow {BATCH} {exploring} {depth} {ms:.0f}")
            fields = dict(word.split("=") for word in header.split()[1:])
            return int(fields["expanded"]), int(fields["engine_leaves"])
        leaves = self._leaves(helper, BATCH, exploring)
        if not leaves:
            return 0, 0
        return self._expand(helper, pool, leaves, depth, deadline)

    def _leaves(self, helper: Helper, count: int, exploring: int) -> list[tuple[int, FowBoard]]:
        _, rows = helper.ask(f"tree leaves {count} {exploring}", time.monotonic() + ANSWER_SECONDS)
        out = []
        for row in rows:
            _, node, fen = row.split(" ", 2)
            out.append((int(node), FowBoard(fen)))
        return out

    def _expand(self, helper: Helper, pool: EnginePool | None, leaves: list[tuple[int, FowBoard]],
                depth: int, deadline: float) -> tuple[int, int]:
        """Have Stockfish value every leaf's children (one MultiPV call each) and hand the
        helper the rows; it adds the children. Returns (expanded, engine-valued leaves)."""
        tables: dict[int, dict[str, float]] = {}
        if pool is not None and pool.ready_count() > 0:
            jobs, owners = [], []
            for node, board in leaves:
                if engine_accepts(board):
                    jobs.append(Job(engine_fen(board), depth))
                    owners.append(node)
            if jobs:
                for node, result in zip(owners, pool.run(jobs, deadline, *LEAF_SLICE), strict=True):
                    if result is None or result.no_moves:
                        continue
                    found = result.complete_depth(list(result.scores))
                    if found is not None:
                        tables[node] = {uci: scores[found] for uci, scores in result.scores.items()
                                        if found in scores}
        rows = []
        for node, _ in leaves:
            table = tables.get(node, {})
            rows.append(f"c {node} {len(table)} " + " ".join(f"{uci} {v:.6f}" for uci, v in table.items()))
        header = self._ask(helper, f"tree children {len(rows)}\n" + "\n".join(rows))
        fields = dict(word.split("=") for word in header.split()[1:])
        return int(fields["expanded"]), int(fields["engine_leaves"])
