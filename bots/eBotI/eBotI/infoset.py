"""Two plies with the fog in them: what a move is worth when our next move must be chosen
without seeing the opponent's reply.

Stockfish's value of a board after our move assumes we see the opponent's reply before
we move again. In Fog of War we do not: a rook that swings onto an open line towards our
king, a bishop that comes to bear on a piece, stay unseen until they strike. So the
engine's value is an upper bound (Jensen: the expectation over boards of a maximum is at
least the maximum of the expectation), and the bound is loosest for the moves that leave
most of the board out of sight. This is the error behind most of our arena losses: the
material and the king are lost two to five plies after a move the engine liked.

The correction, over the belief states the engine scored: for each candidate move m,
each state b and each likely reply r (the same one-ply model that weights the belief),
compute what we will SEE after r. Group the (b, r) pairs by that view. Our next move must
be the same within a group, so the group's value is the best single move for the whole
group, and the value of m is the weighted mean over groups. Where the engine thought we
would dodge a threat we cannot see, this value says we lose the piece.
"""
from __future__ import annotations

import math
import os
import time
from collections import defaultdict
from collections.abc import Sequence

import chess
import numpy as np

from referee import FowBoard, fow_moves, observation
from .engine import EnginePool, Job
from .opponent import LOSS as OPP_LOSS, POLICY_TEMPERATURE
from .rules import side_to_move_wins
from .stockfish_search import engine_accepts, engine_fen, LOSS, WIN

INFOSET = os.environ.get("FOW_INFOSET", "0") == "1"
CANDIDATES = int(os.environ.get("FOW_INFOSET_CANDS", "5"))   # our moves refined, the best by the one-ply value
STATES = int(os.environ.get("FOW_INFOSET_STATES", "12"))     # belief states used, the heaviest
REPLIES = int(os.environ.get("FOW_INFOSET_REPLIES", "3"))    # opponent replies per state, the likeliest
DEPTH = int(os.environ.get("FOW_INFOSET_DEPTH", "6"))        # engine depth after the reply
SHARE = float(os.environ.get("FOW_INFOSET_SHARE", "0.5"))    # of the move's budget
MIX = float(os.environ.get("FOW_INFOSET_MIX", "1.0"))        # 1: the two-ply value alone; 0: the one-ply value alone
REPLY_DEPTH = 1
MIN_SLICE = 0.01


def _reply_odds(values: dict[str, float], temperature: float = POLICY_TEMPERATURE) -> dict[str, float]:
    top = max(values.values())
    w = {m: math.exp((v - top) / temperature) for m, v in values.items()}
    total = sum(w.values())
    return {m: x / total for m, x in w.items()}


def refine(pool: EnginePool, states: Sequence[FowBoard], weights: Sequence[float],
           our_moves: Sequence[chess.Move], values: np.ndarray, side: chess.Color,
           deadline: float, log=None) -> np.ndarray | None:
    """``values`` (one-ply, per move) with the two-ply fog value put in for the best
    CANDIDATES moves. None if nothing could be computed in time."""
    if len(states) == 0 or pool.ready_count() == 0:
        return None
    order = np.argsort(-values)
    cands = [int(i) for i in order[:CANDIDATES] if values[i] > LOSS + 1e-9]
    if len(cands) < 2:
        return None
    heavy = np.argsort(-np.asarray(weights, dtype=float))[:STATES]
    boards = [states[i] for i in heavy]
    board_weight = [max(float(weights[i]), 0.0) for i in heavy]

    # 1. The opponent's likely replies on each (candidate, state).
    reply_jobs, reply_owner, after_move = [], [], {}
    for c in cands:
        move = our_moves[c]
        for b, board in enumerate(boards):
            if move not in board.pseudo_legal_moves and not board.is_legal(move):
                continue
            child = board.copy(stack=False)
            child.push(move)
            if side_to_move_wins(child):
                after_move[(c, b)] = None          # loses the king at once: LOSS, no replies needed
                continue
            if not engine_accepts(child):
                continue
            after_move[(c, b)] = child
            reply_jobs.append(Job(engine_fen(child), REPLY_DEPTH))
            reply_owner.append((c, b))
    if not reply_jobs:
        return None
    now = time.monotonic()
    reply_deadline = now + 0.25 * (deadline - now)
    results = pool.run(reply_jobs, reply_deadline, MIN_SLICE, MIN_SLICE * 4)

    # 2. After each reply: our view, and the engine's value of every move of ours.
    leaf_jobs, leaf_owner = [], []
    pairs = defaultdict(list)  # (c) -> list of (b, reply uci, prob)
    for (c, b), result in zip(reply_owner, results, strict=True):
        if result is None or result.no_moves:
            continue
        depth = result.complete_depth(list(result.scores))
        if depth is None:
            continue
        child = after_move[(c, b)]
        legal = {m.uci() for m in fow_moves(child)}
        vals = {m: f[depth] for m, f in result.scores.items() if m in legal}
        if not vals:
            continue
        odds = _reply_odds(vals)
        top = sorted(odds, key=lambda m: -odds[m])[:REPLIES]
        norm = sum(odds[m] for m in top)
        for uci in top:
            reply = chess.Move.from_uci(uci)
            leaf = child.copy(stack=False)
            leaf.push(reply)
            prob = odds[uci] / norm
            if side_to_move_wins(leaf):     # the reply takes our king (the engine rated it a capture; the belief its risk)
                pairs[c].append((b, uci, prob, None, None))
                continue
            if not engine_accepts(leaf):
                continue
            view = observation(leaf, side)
            pairs[c].append((b, uci, prob, view, len(leaf_jobs)))
            leaf_jobs.append(Job(engine_fen(leaf), DEPTH))
            leaf_owner.append((c, b, uci, leaf))
    if not leaf_jobs:
        return None
    results = pool.run(leaf_jobs, deadline, MIN_SLICE, max(MIN_SLICE, (deadline - time.monotonic()) / max(1, len(leaf_jobs)) * 4))
    leaf_values: dict[int, dict[str, float]] = {}
    for j, ((c, b, uci, leaf), result) in enumerate(zip(leaf_owner, results, strict=True)):
        if result is None:
            continue
        if result.no_moves:
            leaf_values[j] = {}
            continue
        depth = result.complete_depth(list(result.scores))
        if depth is None:
            continue
        table = {m: f[depth] for m, f in result.scores.items()}
        # moves that lose the king at once are not in the engine's list: LOSS when chosen
        leaf_values[j] = table

    # 3. Group by view; one move per group; weighted mean per candidate.
    refined = values.astype(float).copy()
    done = 0
    for c in cands:
        groups: dict[str, list[tuple[float, dict[str, float] | None]]] = defaultdict(list)
        total = 0.0
        for b, uci, prob, view, j in pairs[c]:
            w = board_weight[b] * prob
            if view is None:                 # our king was taken
                groups["lost:" + uci + str(b)].append((w, None))
            elif j in leaf_values:
                groups[view].append((w, leaf_values[j]))
            else:
                continue
            total += w
        for b in range(len(boards)):
            if (c, b) in after_move and after_move[(c, b)] is None:
                groups["suicide:" + str(b)].append((board_weight[b], None))
                total += board_weight[b]
        if total <= 0:
            continue
        value = 0.0
        for members in groups.values():
            if all(t is None for _, t in members):
                value += sum(w for w, _ in members) * LOSS
                continue
            # the best single move for the whole group: a move missing from a board's table
            # loses the king there (or is impossible there), so it counts LOSS on that board
            moves = set()
            for _, t in members:
                if t:
                    moves |= t.keys()
            best = LOSS
            for m in moves:
                s = sum(w * (t.get(m, LOSS) if t is not None else LOSS) for w, t in members)
                best = max(best, s / sum(w for w, _ in members))
            value += best * sum(w for w, _ in members)
        refined[c] = (1.0 - MIX) * values[c] + MIX * value / total
        done += 1
    if log is not None:
        log(f"infoset: {done}/{len(cands)} candidates, {len(boards)} states, {len(reply_jobs)} reply jobs, "
            f"{len(leaf_jobs)} leaves scored {len(leaf_values)}, "
            + " ".join(f"{our_moves[c].uci()}:{values[c]:+.3f}->{refined[c]:+.3f}" for c in cands))
    return refined
