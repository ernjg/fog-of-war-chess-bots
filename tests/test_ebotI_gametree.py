"""eBotI: the growing game tree solves known games, grows, and carries over between turns."""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bots" / "eBotI"))

import fow  # noqa: E402,F401
import chess  # noqa: E402
from referee import FowBoard, fow_moves, observation  # noqa: E402

from eBotI.engine import EnginePool  # noqa: E402
from eBotI.gametree import NEVER_EXIT, OURS, THEIRS, GameTree  # noqa: E402
from eBotI.obscuro_search import ObscuroSearch  # noqa: E402

FAKE = [sys.executable, str(Path(__file__).with_name("fake_uci_engine.py"))]


@pytest.fixture
def pool(monkeypatch):
    monkeypatch.setenv("FAKE_UCI", "")
    monkeypatch.setenv("FAKE_UCI_SCORES", "{}")
    pool = EnginePool.start(FAKE, 2, time.monotonic() + 5)
    yield pool
    pool.close()


def start_tree(boards, obs=None):
    tree = GameTree(chess.WHITE, random.Random(0))
    moves = tuple(sorted(boards[0].generate_pseudo_legal_moves(), key=chess.Move.uci))
    tree.set_root_view(obs or observation(boards[0], chess.WHITE), moves)
    roots = [tree.add_root(b, tree.new_J(NEVER_EXIT), 1.0) for b in boards]
    return tree, roots, moves


def test_root_expansion_groups_roots_into_one_infoset_and_solves(pool) -> None:
    tree, roots, moves = start_tree([FowBoard()])
    tree.expand_nodes(roots, pool, time.monotonic() + 5)
    assert tree.root_infoset >= 0 and tree.n_children[roots[0]] == len(moves)
    tree.iterate()
    strategy = tree.root_strategy()
    assert strategy.shape == (len(moves),) and np.isclose(strategy.sum(), 1.0)
    for _ in range(50):
        tree.iterate()
    assert tree.iterations == 51 and -1 <= tree.value() <= 1


def test_terminal_children_are_decided_without_the_engine(pool) -> None:
    # White Ke1 vs Black Ke8 and Re7: Ke1-e2 walks into the rook, a loss for us at once.
    root = FowBoard("4k3/4r3/8/8/8/8/8/4K3 w - - 0 1")
    tree, roots, moves = start_tree([root])
    tree.expand_nodes(roots, pool, time.monotonic() + 5)
    k = moves.index(chess.Move.from_uci("e1e2"))
    child = tree.first_child[roots[0]] + k
    assert tree.terminal[child] and tree.leaf_value[child] == -1.0


def test_growth_adds_deeper_layers_and_values_leaves_with_the_engine(pool) -> None:
    tree, roots, moves = start_tree([FowBoard()])
    tree.expand_nodes(roots, pool, time.monotonic() + 5)
    tree.iterate()
    before = tree.n_nodes
    for step in range(6):
        leaves = tree.choose_leaves(4, step % 2)
        assert leaves, "the walk must reach an unexpanded leaf"
        tree.expand_nodes(leaves, pool, time.monotonic() + 5)
        tree.iterate()
    assert tree.n_nodes > before and max(tree.depth) >= 2
    assert tree.n_infosets > 1 and tree.n_slots[THEIRS] > 0
    for _ in range(20):
        tree.iterate()
    assert np.isclose(tree.root_strategy().sum(), 1.0)


def test_carry_over_builds_the_next_turn_from_the_old_tree(pool) -> None:
    tree, roots, moves = start_tree([FowBoard()])
    tree.expand_nodes(roots, pool, time.monotonic() + 5)
    tree.iterate()
    # expand every opponent reply to e2e4 so the next turn has roots to carry
    k = moves.index(chess.Move.from_uci("e2e4"))
    reply_node = tree.first_child[roots[0]] + k
    tree.expand_nodes([reply_node], pool, time.monotonic() + 5)
    for _ in range(10):
        tree.iterate()
    board = FowBoard(); board.push_uci("e2e4"); board.push_uci("e7e5")
    obs = observation(board, chess.WHITE)
    our_moves = tuple(sorted(fow_moves(board), key=chess.Move.uci))
    new = tree.carry_over(chess.Move.from_uci("e2e4"), obs, our_moves, max_kluss=50)
    assert new.boards, "the matching reply became a root"
    new.expand_nodes(list(new.boards), pool, time.monotonic() + 5)
    assert new.root_infoset >= 0
    carried = new.iset_nodes[new.root_infoset]
    assert len(carried) >= 1
    assert all(observation(new.boards[n], chess.WHITE) == obs for n in carried)
    # roots the opponent cannot tell apart from ours (other replies with the same view) are KLUSS roots
    assert len(new.boards) >= len(carried)
    assert len(new.alt) == len(set(new.root_J[n] for n in new.boards))
    assert all(-1.0 <= a <= 1.0 for a in new.alt)
    new.finish_gadget()
    for _ in range(5):
        new.iterate()
    assert np.isclose(new.root_strategy().sum(), 1.0)


def test_full_search_two_turns_returns_legal_moves(pool) -> None:
    rng = random.Random(1)
    search = ObscuroSearch(chess.WHITE, rng)
    board = FowBoard()
    moves = list(board.generate_pseudo_legal_moves())
    result = search.search([board], moves, observation(board, chess.WHITE), 1.0, pool)
    assert result is not None and result.move in moves and result.roots == 1
    search.record(result.move)
    board.push(result.move)
    reply = rng.choice(list(fow_moves(board)))
    board.push(reply)
    moves = list(fow_moves(board))
    second = search.search([board], moves, observation(board, chess.WHITE), 1.0, pool)
    assert second is not None and second.move in moves
    assert second.carried + second.kluss + 1 >= second.roots or second.roots >= 1


def hand_built_pennies(hidden: bool) -> GameTree:
    """Matching pennies as a tree: one root (ours, 2 moves), two opponent nodes with 2 replies
    each, payoffs [[1, -1], [-1, 1]]. hidden=True puts both opponent nodes in one infoset."""
    from eBotI.gametree import ROOT_PREV, _grow
    tree = GameTree(chess.WHITE, random.Random(0))
    J = tree.new_J(NEVER_EXIT)
    m = [chess.Move.from_uci("a2a3"), chess.Move.from_uci("b2b3")]
    root = tree._add_node(-1, None, 0, OURS, (ROOT_PREV, ("J", J)), J, 1.0)
    tree.boards[root] = FowBoard()

    def new_infoset(player, moves, nodes, initial):
        iset = len(tree.iset_player)
        tree.iset_player.append(player); tree.iset_start.append(tree.n_slots[player])
        tree.iset_moves.append(tuple(moves)); tree.iset_nodes.append(list(nodes)); tree.iset_visits.append(0)
        tree.rm[player] = _grow(tree.rm[player], np.full(len(moves), iset, dtype=np.int64), iset + 1, np.array(initial))
        for name, fill in (("visits", 0.0), ("u_count", 2.0), ("u_sum", 0.0), ("u_sq", 2.0)):
            arrays = getattr(tree, name); arrays[player] = np.concatenate([arrays[player], np.full(len(moves), fill)])
        start = tree.n_slots[player]; tree.n_slots[player] += len(moves)
        for n in nodes:
            tree.infoset[n] = iset; tree.expanded[n] = True
        return iset, start

    ours, start = new_infoset(OURS, m, [root], [0.9, 0.1])
    tree.root_infoset = ours
    opp_nodes = []
    for a in range(2):
        n = tree._add_node(root, m[a], 1, THEIRS, ((ours, start + a), ("J", J)), slot=start + a)
        opp_nodes.append(n)
    tree.first_child[root], tree.n_children[root] = opp_nodes[0], 2
    payoff = [[1.0, -1.0], [-1.0, 1.0]]
    groups = [opp_nodes] if hidden else [[opp_nodes[0]], [opp_nodes[1]]]
    for group in groups:
        iset, s0 = new_infoset(THEIRS, m, group, [0.5, 0.5])
        for n in group:
            a = opp_nodes.index(n)
            first = len(tree.parent)
            for b in range(2):
                leaf = tree._add_node(n, m[b], 2, OURS, ((ours, start + a), (iset, s0 + b)), slot=s0 + b)
                tree.leaf_value[leaf] = payoff[a][b]
            tree.first_child[n], tree.n_children[n] = first, 2
    tree.finish_gadget()
    return tree


def test_hidden_matching_pennies_mixes_to_a_half() -> None:
    tree = hand_built_pennies(hidden=True)
    for _ in range(3000):
        tree.iterate()
    assert np.allclose(tree.root_strategy(), 0.5, atol=0.05)
    assert abs(tree.value()) < 0.05


def test_visible_matching_pennies_is_lost() -> None:
    tree = hand_built_pennies(hidden=False)
    for _ in range(300):
        tree.iterate()
    assert tree.value() == pytest.approx(-1.0, abs=1e-6)


@pytest.mark.parametrize("alt, exits", [(-0.5, True), (0.5, False)])
def test_resolve_gadget_exits_when_the_alternate_value_is_better(alt: float, exits: bool) -> None:
    tree = hand_built_pennies(hidden=True)   # game value 0 for us
    tree.alt[0] = alt                        # our value if the opponent exits
    tree.finish_gadget()
    for _ in range(500):
        tree.iterate()
    if exits:    # exiting hands us -0.5, which the opponent prefers to the 0 of playing on
        assert tree.pmax < 0.05
        assert tree.margins()[0] > 0           # safe: Maxmargin takes over
    else:
        assert tree.pmax > 0.95
