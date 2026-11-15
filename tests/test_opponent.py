"""The opponent policy: Stockfish's scores turned into odds for the opponent's moves."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402

from fow.obscuro.engine import EnginePool  # noqa: E402
from fow.obscuro.opponent import (KING_MISS, OTHER, POLICY_SHARE, OpponentPolicy,  # noqa: E402
                                  move_odds)
from referee import FowBoard, fow_moves  # noqa: E402

FAKE = [sys.executable, str(Path(__file__).with_name("fake_uci_engine.py"))]
QUEEN_HANGS = "4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1"          # exd5 wins the queen


@pytest.fixture
def pool(monkeypatch):
    monkeypatch.setenv("FAKE_UCI", "")
    monkeypatch.setenv("FAKE_UCI_SCORES", "{}")
    started = EnginePool.start(FAKE, 2, time.monotonic() + 5)
    yield started
    started.close()


def test_move_odds_sum_to_one_and_follow_the_scores() -> None:
    values = {"a": 0.5, "b": 0.5, "c": 0.0, "d": -0.9}
    odds = move_odds(values, n_moves=6)  # two more moves that Stockfish does not list
    total = sum(odds[move] for move in values) + 2 * odds[OTHER]
    assert total == pytest.approx(1.0)
    assert odds["a"] == odds["b"] > odds["c"] > odds["d"] > odds[OTHER] > 0
    # Equal odds get their fixed share whatever the scores say: no move is ever ruled out.
    assert odds[OTHER] == pytest.approx((1 - POLICY_SHARE) / 6, rel=1e-3)
    assert odds["a"] == pytest.approx(POLICY_SHARE / 2 + (1 - POLICY_SHARE) / 6, rel=1e-3)


def test_move_odds_with_equal_scores_are_equal_odds() -> None:
    odds = move_odds({"a": 0.1, "b": 0.1, "c": 0.1}, n_moves=3)
    assert odds["a"] == odds["b"] == odds["c"] == pytest.approx(1 / 3)
    hot = move_odds({"a": 0.1, "b": 0.0}, n_moves=2, temperature=0.01)
    cold = move_odds({"a": 0.1, "b": 0.0}, n_moves=2, temperature=10.0)
    assert hot["a"] > cold["a"] > 0.5  # a low temperature trusts the scores more


def test_policy_prefers_the_move_stockfish_prefers(pool) -> None:
    board = FowBoard(QUEEN_HANGS)
    moves = fow_moves(board)
    policy = OpponentPolicy(pool)
    (table,) = policy([board], [len(moves)])
    assert table is not None and policy.asked == policy.answered == 1
    total = sum(table.get(move.uci(), table[OTHER]) for move in moves)
    assert total == pytest.approx(1.0)
    best = max(moves, key=lambda move: table.get(move.uci(), table[OTHER]))
    assert best.uci() == "e4d5" and table["e4d5"] > 0.8  # the scripted engine values the queen at 900


def test_a_side_that_did_not_take_the_king_was_unlikely_to_be_able_to(pool) -> None:
    board = FowBoard("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")  # White to move could take the king
    moves = fow_moves(board)
    (table,) = OpponentPolicy(pool)([board], [len(moves)])
    assert table == {OTHER: KING_MISS / len(moves)}


def test_policy_gives_no_table_where_it_has_no_answer(pool, monkeypatch) -> None:
    fine = FowBoard(QUEEN_HANGS)
    impossible = FowBoard("4k3/8/8/8/8/8/PPPPPPPP/QQ2K3 w - - 0 1")  # Stockfish would exit on it
    policy = OpponentPolicy(pool)
    tables = policy([impossible, fine], [len(fow_moves(impossible)), len(fow_moves(fine))])
    assert tables[0] is None and tables[1] is not None
    assert pool.deaths == 0 and pool.ready_count() == 2  # it was never sent

    for engine in pool.engines:  # with the engines gone: no tables, and no exception
        engine.kill()
    assert policy([fine], [len(fow_moves(fine))]) == [None]


def test_policy_stops_at_its_time_allowance(monkeypatch) -> None:
    monkeypatch.setenv("FAKE_UCI", "think=0.03")  # every answer takes 30 ms
    monkeypatch.setenv("FAKE_UCI_SCORES", "{}")
    slow = EnginePool.start(FAKE, 1, time.monotonic() + 5)
    try:
        board = FowBoard(QUEEN_HANGS)
        policy = OpponentPolicy(slow, seconds=0.1)
        began = time.monotonic()
        tables = policy([board] * 50, [len(fow_moves(board))] * 50)
        assert time.monotonic() - began < 1.0
        answered = [table is not None for table in tables]
        assert len(tables) == 50 and 1 <= sum(answered) <= 4   # what fitted in a tenth of a second
        assert answered == sorted(answered, reverse=True)      # the first ones asked, in order
        assert slow.ready_count() == 1                         # and the engine is not killed for it
    finally:
        slow.close()
