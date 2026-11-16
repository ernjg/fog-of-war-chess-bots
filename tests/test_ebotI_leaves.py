"""eBotI: the PCFR+ tree takes its leaf values from Stockfish when an engine pool is given."""
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
from referee import FowBoard  # noqa: E402

from eBotI.engine import EnginePool, cp_value  # noqa: E402
from eBotI.evaluation import evaluate  # noqa: E402
from eBotI.search import search  # noqa: E402
from eBotI.subgame import LOSS, SubgameBuilder  # noqa: E402

FAKE = [sys.executable, str(Path(__file__).with_name("fake_uci_engine.py"))]


@pytest.fixture
def pool(monkeypatch):
    monkeypatch.setenv("FAKE_UCI", "")
    monkeypatch.setenv("FAKE_UCI_SCORES", '{"e7e5": 300}')
    pool = EnginePool.start(FAKE, 2, time.monotonic() + 5)
    yield pool
    pool.close()


def leaf(game, builder, our_move: str, reply: str) -> float:
    action = [m.uci() for m in builder.our_moves].index(our_move)
    node = 0 * game.n_actions + action
    board = FowBoard(); board.push_uci(our_move)
    replies = sorted(board.generate_pseudo_legal_moves(), key=chess.Move.uci)
    offset = [m.uci() for m in replies].index(reply)
    slot = builder._infosets[(fow_obs(board), tuple(m.uci() for m in replies))][0] + offset
    hits = np.flatnonzero((game.leaf_node == node) & (game.leaf_slot == slot))
    assert len(hits) == 1
    return float(game.leaf_value[hits[0]])


def fow_obs(board):
    from referee import observation
    return observation(board, chess.BLACK)


def test_leaf_takes_the_engine_value_with_the_sign_turned(pool) -> None:
    moves = list(FowBoard().generate_pseudo_legal_moves())
    builder = SubgameBuilder(moves, chess.WHITE, pool, time.monotonic() + 5)
    assert builder.add_root(FowBoard())
    game = builder.build()
    assert builder.engine_leaves > 0
    # The fake engine scores e7e5 at +300 for Black (to move); for us that is -cp_value(300).
    assert leaf(game, builder, "e2e4", "e7e5") == pytest.approx(-cp_value(300))


def test_without_a_pool_the_heuristic_scores_the_leaves() -> None:
    moves = list(FowBoard().generate_pseudo_legal_moves())
    builder = SubgameBuilder(moves, chess.WHITE)
    builder.add_root(FowBoard())
    game = builder.build()
    board = FowBoard(); board.push_uci("e2e4"); board.push_uci("e7e5")
    assert builder.engine_leaves == 0
    assert leaf(game, builder, "e2e4", "e7e5") == pytest.approx(evaluate(board, chess.WHITE))


def test_terminal_nodes_stay_decided_without_the_engine(pool) -> None:
    # White Ke1 against Black Ke8, Re7: after Ke1-e2 the rook takes our king: a loss, no engine call.
    root = FowBoard("4k3/4r3/8/8/8/8/8/4K3 w - - 0 1")
    moves = list(root.generate_pseudo_legal_moves())
    builder = SubgameBuilder(moves, chess.WHITE, pool, time.monotonic() + 5)
    assert builder.add_root(root)
    game = builder.build()
    action = [m.uci() for m in moves].index("e1e2")
    assert game.terminal_value[action] == LOSS


def test_search_with_a_pool_returns_a_legal_move(pool) -> None:
    board = FowBoard()
    moves = list(board.generate_pseudo_legal_moves())
    result = search([board], moves, chess.WHITE, budget=1.0, rng=random.Random(0), pool=pool)
    assert result is not None and result.move in moves and result.engine_leaves > 0
