"""The UCI engine pool against a scripted engine: normal searches and every fault we guard."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402

from fow.obscuro.engine import (EnginePool, Job, JobResult, cp_value, mate_value,  # noqa: E402
                                parse_info)

FAKE = [sys.executable, str(Path(__file__).with_name("fake_uci_engine.py"))]
MIDDLEGAME = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
QUEEN_HANGS = "4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1"
CHECKMATED = "7k/5QQ1/8/8/8/8/8/K7 b - - 0 1"
STALEMATED = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"


@pytest.fixture
def start(monkeypatch):
    """Start a pool of fake engines with the given fault options; closed after the test."""
    pools = []

    def _start(count: int = 2, faults: str = "", seconds: float = 5.0, scores: str = "{}"):
        monkeypatch.setenv("FAKE_UCI", faults)
        monkeypatch.setenv("FAKE_UCI_SCORES", scores)
        pool = EnginePool.start(FAKE, count, time.monotonic() + seconds)
        pools.append(pool)
        return pool

    yield _start
    for pool in pools:
        pool.close()


def legal_ucis(fen: str) -> list[str]:
    return [move.uci() for move in chess.Board(fen).legal_moves]


def test_parse_info_reads_real_stockfish_lines() -> None:
    assert parse_info("info depth 6 seldepth 9 multipv 3 score cp -12 nodes 5 nps 1 hashfull 0 "
                      "tbhits 0 time 1 pv e2e4 e7e5") == (6, 3, "e2e4", cp_value(-12))
    assert parse_info("info depth 4 seldepth 2 multipv 1 score mate 1 nodes 3688 nps 1229333 "
                      "hashfull 0 tbhits 0 time 3 pv a1a8") == (4, 1, "a1a8", mate_value(1))
    for line in ("info depth 0 score mate 0", "info depth 0 score cp 0", "info string NNUE evaluation",
                 "info depth 12 currmove e2e4 currmovenumber 1", "bestmove e2e4 ponder e7e5", "",
                 "info depth 3 seldepth 3 multipv 1 score cp 10 lowerbound nodes 1 nps 1 hashfull 0 "
                 "tbhits 0 time 1 pv e2e4", "info depth x score cp y pv z",
                 "info depth x seldepth 3 multipv 1 score cp 10 nodes 1 nps 1 hashfull 0 tbhits 0 "
                 "time 1 pv e2e4",
                 "info depth 3 seldepth 3 multipv 1 score cp ten nodes 1 nps 1 hashfull 0 tbhits 0 "
                 "time 1 pv e2e4",
                 # What Stockfish prints for moves it was stopped before searching:
                 "info depth 1 seldepth 0 multipv 1 score cp 0 nodes 0 nps 0 hashfull 0 tbhits 0 "
                 "time 0 pv e2e4",
                 "info depth 1 seldepth 0 multipv 2 score cp 0 nodes 0 nps 0 hashfull 0 tbhits 0 "
                 "time 0 pv"):
        assert parse_info(line) is None


def test_values_are_ordered_loss_mate_cp_mate_win() -> None:
    assert -1.0 < mate_value(-1) < mate_value(-20) < cp_value(-100000) < cp_value(-50) < 0
    assert 0 < cp_value(50) < cp_value(100000) < mate_value(20) < mate_value(1) < 1.0
    assert mate_value(0) == -1.0  # the side to move is already mated
    # No flat top: the larger of two winning scores is still worth more.
    assert cp_value(1600) < cp_value(1700) < cp_value(2500) < cp_value(6000) < cp_value(19000)
    assert cp_value(100000) == pytest.approx(0.99) and cp_value(0) == 0.0
    assert cp_value(-2500) == -cp_value(2500)


def test_complete_depth_needs_every_move() -> None:
    result = JobResult({"a": {1: 0.1, 2: 0.2, 3: 0.3}, "b": {1: 0.5, 2: 0.4}}, False, True)
    assert result.complete_depth(["a", "b"]) == 2
    assert result.complete_depth(["a"]) == 3
    assert result.complete_depth(["a", "c"]) is None
    assert result.complete_depth([]) is None
    assert result.best() == 0.4  # depth 2 is the deepest that covers both moves
    assert JobResult({}, True, False).best() is None


def test_pool_scores_every_legal_move_and_ends_idle(start) -> None:
    pool = start(2)
    assert pool.ready_count() == 2
    fens = [MIDDLEGAME, QUEEN_HANGS, chess.STARTING_FEN] * 3
    results = pool.run([Job(fen, 3) for fen in fens], time.monotonic() + 5, 0.02, 1.0)
    for fen, result in zip(fens, results, strict=True):
        assert result is not None and not result.no_moves and not result.stopped
        assert result.complete_depth(legal_ucis(fen)) == 3
    assert results[1].scores["e4d5"][3] == cp_value(900)  # the pawn takes the queen
    assert pool.ready_count() == 2 and pool.deaths == 0
    again = pool.run([Job(MIDDLEGAME, 1)], time.monotonic() + 5, 0.02, 1.0)  # reusable
    assert again[0].complete_depth(legal_ucis(MIDDLEGAME)) == 1


def test_no_legal_moves_is_reported(start) -> None:
    pool = start(1)
    mated, stalemated = pool.run([Job(CHECKMATED, 3), Job(STALEMATED, 3)],
                                 time.monotonic() + 5, 0.02, 1.0)
    assert mated.no_moves and stalemated.no_moves
    assert mated.scores == {} and mated.best() is None


def test_slice_stops_a_long_search_and_keeps_completed_depths(start) -> None:
    pool = start(1, "slow=0.05")
    began = time.monotonic()
    (result,) = pool.run([Job(MIDDLEGAME, 50)], began + 5, 0.02, 0.2)
    assert 0.15 < time.monotonic() - began < 1.0
    assert result.stopped
    assert 2 <= result.complete_depth(legal_ucis(MIDDLEGAME)) < 50


def test_deadline_cuts_running_jobs_and_skips_the_rest(start) -> None:
    pool = start(1, "slow=0.05")
    began = time.monotonic()
    results = pool.run([Job(MIDDLEGAME, 50)] * 4, began + 0.3, 0.25, 1.0)
    elapsed = time.monotonic() - began
    # The first job runs its 0.25 s slice; the second is cut by the deadline 0.05 s later.
    # If the deadline did not cut it, it would run its own 0.25 s and end at 0.5 s.
    assert 0.28 < elapsed < 0.42
    assert [result is not None and result.stopped for result in results] == [True, True, False, False]
    assert results[2] is None and results[3] is None  # never started
    assert pool.ready_count() == 1  # idle, not killed


def test_report_after_stop_is_discarded(start) -> None:
    """Stopped mid-iteration, the engine reports some moves one depth deeper and the rest
    at their old scores. None of that report may be used."""
    moves = legal_ucis(MIDDLEGAME)
    for fault in ("partial", "finish", "bound"):  # half a report, a whole one, one led by a bound
        pool = start(1, f"slow=0.2,{fault}")
        # Reports arrive at 0, 0.2 and 0.4 s; "stop" goes out at 0.3 s, after the second.
        (result,) = pool.run([Job(MIDDLEGAME, 50)], time.monotonic() + 5, 0.02, 0.3)
        assert result.stopped and result.complete_depth(moves) == 2, fault
        assert all(sorted(depths) == [1, 2] for depths in result.scores.values()), fault
        assert set(result.scores) == set(moves), fault


def test_search_that_ends_by_itself_keeps_its_last_report(start) -> None:
    pool = start(1, "slow=0.05")
    (result,) = pool.run([Job(MIDDLEGAME, 3)], time.monotonic() + 5, 0.02, 1.0)
    assert not result.stopped and result.complete_depth(legal_ucis(MIDDLEGAME)) == 3


def test_slow_answer_to_stop_is_waited_for(start) -> None:
    """An engine that takes a moment to answer "stop" is not killed for it."""
    pool = start(1, "slow=0.2,late=0.3")
    began = time.monotonic()
    (result,) = pool.run([Job(MIDDLEGAME, 50)], began + 5, 0.02, 0.3)
    assert result is not None and result.stopped and pool.ready_count() == 1
    assert 0.55 < time.monotonic() - began < 1.2


def test_engine_that_exits_loses_only_its_job(start) -> None:
    pool = start(2, "die_at=3")  # each engine: handshake, one job, then it exits
    began = time.monotonic()
    results = pool.run([Job(MIDDLEGAME, 2)] * 6, began + 5, 0.02, 1.0)
    assert time.monotonic() - began < 2.0
    assert [result is not None for result in results] == [True, True, False, False, False, False]
    assert pool.ready_count() == 0 and pool.deaths == 2
    assert pool.run([Job(MIDDLEGAME, 2)], time.monotonic() + 1, 0.02, 1.0) == [None]


def test_one_engine_dying_on_a_position_leaves_the_other_working(start) -> None:
    """Stockfish exits on a position it rejects. Only that job is lost; the other engine
    finishes the queue, and the position is not handed to it."""
    pool = start(2, "die_fen=3q4")
    jobs = [Job(MIDDLEGAME, 2), Job(QUEEN_HANGS, 2), Job(MIDDLEGAME, 2), Job(chess.STARTING_FEN, 2),
            Job(MIDDLEGAME, 2)]
    results = pool.run(jobs, time.monotonic() + 5, 0.02, 1.0)
    assert [result is not None for result in results] == [True, False, True, True, True]
    assert pool.ready_count() == 1 and pool.deaths == 1
    assert "CRITICAL ERROR" in pool.failure


def test_restart_replaces_dead_engines_up_to_the_limit(start, monkeypatch) -> None:
    pool = start(2, "die_at=2")  # dies on its first job
    pool.run([Job(MIDDLEGAME, 1)] * 2, time.monotonic() + 5, 0.02, 1.0)
    assert pool.ready_count() == 0
    monkeypatch.setenv("FAKE_UCI", "")
    assert pool.restart(time.monotonic() + 5) == 2 and pool.ready_count() == 2
    (result,) = pool.run([Job(MIDDLEGAME, 1)], time.monotonic() + 5, 0.02, 1.0)
    assert result is not None
    for engine in pool.engines:
        engine.kill()
    assert pool.restart(time.monotonic() + 5) == 1  # the third and last restart
    assert pool.restarts == pool.restart_limit
    pool.engines[0].kill()
    assert pool.restart(time.monotonic() + 5) == 0 and pool.ready_count() == 0


def test_hung_engine_is_killed_after_stop(start) -> None:
    pool = start(1, "hang_at=2")
    began = time.monotonic()
    results = pool.run([Job(MIDDLEGAME, 5)] * 2, began + 0.2, 0.02, 0.1)
    assert time.monotonic() - began < 1.5
    assert results == [None, None]
    assert pool.ready_count() == 0 and "stop" in pool.failure


def test_mute_engine_fails_the_handshake_in_time(start) -> None:
    began = time.monotonic()
    pool = start(2, "mute", seconds=0.4)
    assert time.monotonic() - began < 2.0
    assert pool.ready_count() == 0 and "uciok" in pool.failure


def test_one_silent_engine_does_not_cost_the_healthy_one(start, tmp_path) -> None:
    """Each engine goes through the handshake on its own: the one that never answers is
    dropped at the deadline, and the one that answered at once is kept and works."""
    began = time.monotonic()
    pool = start(2, f"mute_one={tmp_path / 'silent'}", seconds=1.0)
    assert 0.9 < time.monotonic() - began < 2.5
    assert pool.ready_count() == 1 and pool.deaths == 1
    assert "no uciok in time" in pool.failure
    assert 0 < pool.start_seconds < 0.8  # what the healthy one needed, not how long we waited
    (result,) = pool.run([Job(MIDDLEGAME, 2)], time.monotonic() + 5, 0.02, 1.0)
    assert result is not None and result.complete_depth(legal_ucis(MIDDLEGAME)) == 2


def test_the_reason_an_engine_gives_for_exiting_is_kept(start) -> None:
    """Stockfish puts its reason at the end of a long line, after other long lines."""
    pool = start(1, "die_fen=3q4")
    assert pool.run([Job(QUEEN_HANGS, 2)], time.monotonic() + 5, 0.02, 1.0) == [None]
    assert pool.failure.startswith("exited during a search; last output: ")
    assert pool.failure.endswith("failed. Reason: test.") and len(pool.failure) < 320


def test_missing_binary_is_not_an_error() -> None:
    pool = EnginePool.start([str(ROOT / "no-such-engine")], 2, time.monotonic() + 1)
    assert pool.ready_count() == 0 and "could not start" in pool.failure
    assert pool.run([Job(MIDDLEGAME, 1)], time.monotonic() + 1, 0.02, 1.0) == [None]
    pool.close()


def test_junk_output_is_ignored(start) -> None:
    pool = start(1, "garbage")
    (result,) = pool.run([Job(MIDDLEGAME, 2)], time.monotonic() + 5, 0.02, 1.0)
    assert result.complete_depth(legal_ucis(MIDDLEGAME)) == 2
    assert set(result.scores) == set(legal_ucis(MIDDLEGAME))


def test_engines_share_the_bots_process_group(start) -> None:
    """The arena pauses the bot's process group; an engine outside it would keep running."""
    pool = start(2)
    assert {os.getpgid(engine.proc.pid) for engine in pool.engines} == {os.getpgid(0)}
