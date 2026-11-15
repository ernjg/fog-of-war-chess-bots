"""The obscuro bot charges belief time to its budget and survives internal errors."""
from __future__ import annotations

import importlib.util
import random
import time
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402
from fow.obscuro.search import SearchResult  # noqa: E402
from referee import FowBoard, fow_moves, observation  # noqa: E402

_spec = importlib.util.spec_from_file_location("obscuro_bot", ROOT / "bots" / "obscuro" / "bot.py")
bot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bot)


def make_agent(move_time: float | None = 0.05) -> "bot.ObscuroAgent":
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=move_time)
    agent.reset(chess.WHITE, 180, 2)
    return agent


def play(agent, plies: int, on_turn=None) -> FowBoard:
    """Drive ``agent`` as White against random replies; every move must be FoW-legal.

    Stops early, with Black to move, if Black has no safe reply left (the agent has won).
    Which game is played depends on how much search the agent's time buys, so on a busy
    machine that can happen within a few moves."""
    rng = random.Random(5)
    board = FowBoard()
    for _ in range(plies):
        agent.observe(observation(board, chess.WHITE))
        if board.turn == chess.WHITE:
            if on_turn:
                on_turn(agent, board)
            uci = agent.act(100.0)
            assert uci is not None
            move = chess.Move.from_uci(uci)
            assert move in fow_moves(board)
        else:
            safe = []
            for move in fow_moves(board):
                board.push(move)
                if not board.is_attacked_by(chess.WHITE, board.king(chess.BLACK)):
                    safe.append(move)
                board.pop()
            if not safe:
                break
            move = rng.choice(safe)
        board.push(move)
    return board


def boom(*args, **kwargs):
    raise RuntimeError("boom")


def test_belief_time_is_subtracted_from_the_budget(monkeypatch) -> None:
    agent = make_agent(move_time=None)
    seen = {}

    def fake_search(states, moves, side, budget, rng, repeat_counts=None):
        seen["budget"] = budget
        return None

    monkeypatch.setattr(bot, "search", fake_search)
    agent.observe(observation(FowBoard(), chess.WHITE))
    agent.observe_seconds = 1.5
    agent.act(60.0)
    assert seen["budget"] == pytest.approx(bot.move_budget(58.5, 2) - 1.5)
    assert agent.observe_seconds == 0.0


def test_no_search_when_the_belief_update_used_the_budget(monkeypatch) -> None:
    agent = make_agent(move_time=None)
    monkeypatch.setattr(bot, "search", boom)  # must not be reached
    agent.observe(observation(FowBoard(), chess.WHITE))
    agent.observe_seconds = 30.0
    assert agent.act(10.0) is not None
    assert agent.fallbacks == 1


def test_a_slow_belief_update_still_leaves_a_brief_search_on_a_healthy_clock(monkeypatch) -> None:
    seen = {}

    def fake_search(states, moves, side, budget, rng, repeat_counts=None):
        seen["budget"] = budget
        return None

    monkeypatch.setattr(bot, "search", fake_search)
    agent = make_agent(move_time=None)
    agent.observe(observation(FowBoard(), chess.WHITE))
    agent.observe_seconds = 2.9  # the whole slice this move would get at 42 s on the clock
    assert bot.move_budget(42.0 - 2.9, 2) - 2.9 < bot.MIN_SEARCH_SECONDS
    agent.act(42.0)
    assert seen["budget"] == bot.BRIEF_SEARCH_SECONDS

    # On a low clock nothing is added: the fallback move costs no time at all.
    seen.clear()
    agent = make_agent(move_time=None)
    agent.observe(observation(FowBoard(), chess.WHITE))
    agent.observe_seconds = 2.0
    assert agent.act(15.0) is not None
    assert seen == {} and agent.fallbacks == 1


def many_states(count: int) -> list[FowBoard]:
    return [FowBoard() for _ in range(count)]


def clock_agent(move_time: float | None = None) -> "bot.ObscuroAgent":
    """An agent with the cap the bot really runs with, playing on the clock."""
    agent = bot.ObscuroAgent(seed=1, max_states=1500, move_time=move_time)
    agent.reset(chess.WHITE, 180, 2)
    return agent


def test_the_belief_is_cut_to_what_the_clock_affords() -> None:
    """At 2 ms a state, 0.4 of a move's time at 40 s on the clock pays for 586 states."""
    agent = clock_agent()
    agent.belief.states = many_states(1500)
    agent.state_seconds = 0.002
    agent._fit_belief_to_clock(40.0)
    assert bot.BELIEF_SHARE * bot.move_budget(40.0, 2) / 0.002 == pytest.approx(586.67, abs=0.01)
    assert len(agent.belief) == 586 and agent.belief.max_states == 586 and not agent.belief.exact
    assert agent._belief_size() == "586~/586"

    agent._fit_belief_to_clock(60.0)       # a little more room: not worth moving the cap
    assert agent.belief.max_states == 586
    agent._fit_belief_to_clock(170.0)      # room for half as many again and more: back up
    assert agent.belief.max_states == 1453 and len(agent.belief) == 586
    agent.state_seconds = 0.0005           # a cheap update: the configured cap again
    agent._fit_belief_to_clock(170.0)
    assert agent.belief.max_states == 1500 and agent._belief_size() == "586~"

    agent.state_seconds = 1.0              # absurdly slow: still not below the floor
    agent._fit_belief_to_clock(5.0)
    assert len(agent.belief) == agent.belief.max_states == bot.MIN_BELIEF_STATES


def test_the_belief_is_left_alone_without_a_measurement_or_with_a_fixed_move_time() -> None:
    agent = clock_agent()
    agent.belief.states = many_states(1500)
    agent._fit_belief_to_clock(1.0)        # nothing measured yet
    assert len(agent.belief) == 1500 and agent.belief.exact
    agent = clock_agent(move_time=0.05)    # a fixed time per move is not a clock to fit
    agent.belief.states = many_states(1500)
    agent.state_seconds = 1.0
    agent._fit_belief_to_clock(1.0)
    assert len(agent.belief) == 1500 and agent.belief.max_states == 1500


def test_the_cost_of_an_update_is_measured_on_the_opponents_moves(monkeypatch) -> None:
    agent = make_agent(move_time=None)
    board = FowBoard()
    agent.observe(observation(board, chess.WHITE))
    assert agent.state_seconds is None     # one state says nothing about the cost per state

    def fake_observe(obs, own_move=None, policy=None):
        agent.belief.update_cost = (0.3, 600 if own_move is None else 900)

    monkeypatch.setattr(agent.belief, "observe", fake_observe)
    agent.last_move = chess.Move.from_uci("e2e4")
    agent.observe(observation(board, chess.WHITE))   # after our own move: one move per state
    assert agent.state_seconds is None
    agent.observe(observation(board, chess.WHITE))   # after the opponent's: every move of each
    assert agent.state_seconds == pytest.approx(0.3 / 600)


def test_an_en_passant_capture_no_belief_state_allows_is_left_out(capsys) -> None:
    """The tracker infers the capture e5xd6 from its two observations. A belief rebuilt
    after a failed update has no state with that right: both searches would then reject
    every state. The capture is dropped and the other moves are searched."""
    board = FowBoard()
    for uci in ("e2e4", "h7h6", "e4e5", "d7d5"):
        board.push_uci(uci)
    agent = make_agent(move_time=0.05)
    agent.tracker.observe(observation(board, chess.WHITE))
    capture = chess.Move.from_uci("e5d6")
    moves = fow_moves(board)
    assert capture in moves

    with_right = board.copy(stack=False)
    assert with_right.ep_square == chess.D6
    agent.belief.states = [with_right]
    assert agent._supported(moves) == moves            # a state allows it: nothing changes

    without = board.copy(stack=False)
    without.ep_square = None
    agent.belief.states = [without]
    kept = agent._supported(moves)
    assert capture not in kept and len(kept) == len(moves) - 1
    assert "no belief state allows e5d6" in capsys.readouterr().err
    assert agent._supported([capture]) == [capture]    # the only move is played all the same


def test_the_opponent_policy_is_used_on_the_opponents_moves_only(monkeypatch) -> None:
    agent = make_agent(move_time=0.2)
    agent.pool = StubPool()
    seen = []

    def fake_observe(obs, own_move=None, policy=None):
        seen.append((own_move, policy))

    monkeypatch.setattr(agent.belief, "observe", fake_observe)
    board = FowBoard()
    agent.observe(observation(board, chess.WHITE))            # the starting position
    agent.last_move = chess.Move.from_uci("e2e4")
    agent.observe(observation(board, chess.WHITE))            # after our move
    agent.observe(observation(board, chess.WHITE))            # after the opponent's
    assert [own for own, _ in seen] == [None, chess.Move.from_uci("e2e4"), None]
    assert seen[1][1] is None and seen[0][1] is seen[2][1] is agent.opponent_policy
    assert agent.opponent_policy.pool is agent.pool
    # Its time is a share of the move's, so a quick game does not wait half a second for it.
    assert agent.opponent_policy.seconds == pytest.approx(bot.POLICY_TIME_SHARE * 0.2)

    agent.pool = StubPool(ready=0)                            # no engine running: no policy
    agent.observe(observation(board, chess.WHITE))
    assert seen[-1][1] is None
    agent.pool = None
    agent.observe(observation(board, chess.WHITE))
    assert seen[-1][1] is None

    agent.pool = StubPool()
    agent.weigh_belief = False                                # switched off (--equal-odds)
    agent.observe(observation(board, chess.WHITE))
    assert seen[-1][1] is None


def test_the_search_gets_the_weights_once_the_belief_has_them(monkeypatch) -> None:
    from fow.obscuro.stockfish_search import StockfishResult
    agent = make_agent(move_time=0.3)
    agent.pool = StubPool()
    seen = []

    def fake_stockfish(pool, states, moves, side, budget, rng, repeat_counts=None, weights=None):
        seen.append(weights)
        return StockfishResult(chess.Move.from_uci("g1f3"), 0.1, 0.0, 1, 1, 1, (5, 5), False,
                               tuple(0.0 for _ in moves), tuple(0.0 for _ in moves))

    monkeypatch.setattr(bot, "stockfish_search", fake_stockfish)
    monkeypatch.setattr(agent.belief, "observe", lambda obs, own_move=None, policy=None: None)
    agent.observe(observation(FowBoard(), chess.WHITE))
    agent.act(100.0)
    assert seen == [None]                    # no policy has spoken: every state counts alike
    agent.belief.weighted = True
    agent.belief._weights = [0.25]
    agent.last_move = None
    agent.act(100.0)
    assert seen[-1] == [0.25]


def test_the_log_says_how_much_of_the_belief_the_policy_covered() -> None:
    agent = make_agent()
    assert agent._policy_note() == ""                  # no policy yet
    agent.pool = StubPool()
    policy = agent._policy()
    policy.asked, policy.answered = 650, 412
    assert agent._policy_note() == " policy=412/650"
    assert agent._policy_note() == ""                  # nothing asked since
    policy.asked, policy.answered = 700, 462
    assert agent._policy_note() == " policy=50/50"     # counted from the last move on
    agent.pool = StubPool()                            # new engines, new policy: counts start over
    agent._policy().asked = 3
    assert agent._policy_note() == " policy=0/3"


def test_the_log_shows_what_the_weights_amount_to() -> None:
    agent = clock_agent()
    agent.belief.states = many_states(4)
    assert agent._belief_size() == "4"
    agent.belief._weights = [1.0, 1.0, 0.0, 0.0]
    agent.belief.weighted = True
    assert agent._belief_size() == "4 ess=2"


def test_search_error_still_plays_a_legal_move(monkeypatch) -> None:
    agent = make_agent()
    monkeypatch.setattr(bot, "search", boom)
    play(agent, 12)
    assert agent.fallbacks == 6


def test_belief_update_error_rebuilds_and_keeps_playing() -> None:
    agent = make_agent()
    broken = {"left": 3}
    real = agent.belief.observe

    def flaky(obs, own_move=None):
        if broken["left"] > 0:
            broken["left"] -= 1
            raise RuntimeError("boom")
        return real(obs, own_move=own_move)

    agent.belief.observe = flaky
    board = play(agent, 14)
    assert agent.belief_ok and agent.belief.states and agent.belief.repairs >= 3
    obs = observation(board, chess.WHITE)
    agent.observe(obs)
    for state in agent.belief.states:
        for square, char in enumerate(obs):
            if char != "?":
                piece = state.piece_at(square)
                assert (piece.symbol() if piece else "-") == char


def test_unusable_belief_falls_back_then_recovers(monkeypatch) -> None:
    agent = make_agent()
    monkeypatch.setattr(agent.belief, "observe", boom)
    monkeypatch.setattr(agent.belief, "repair", boom)
    play(agent, 4)
    assert not agent.belief_ok and agent.fallbacks == 2
    monkeypatch.undo()
    play_more = FowBoard()
    agent.reset(chess.WHITE, 180, 2)
    agent.belief_ok = False
    agent.observe(observation(play_more, chess.WHITE))
    assert agent.belief_ok


def test_legal_move_error_retries_without_en_passant(monkeypatch) -> None:
    agent = make_agent()
    agent.observe(observation(FowBoard(), chess.WHITE))
    monkeypatch.setattr(agent.tracker, "legal_moves", boom)
    assert chess.Move.from_uci(agent.act(100.0)) in fow_moves(FowBoard())


def test_repeated_move_is_passed_to_search_with_its_count(monkeypatch) -> None:
    agent = make_agent()
    seen = []

    def fake_search(states, moves, side, budget, rng, repeat_counts=None):
        seen.append(None if repeat_counts is None else dict(zip([m.uci() for m in moves], repeat_counts)))
        return SearchResult(chess.Move.from_uci("g1f3"), 0.5, 0.0, 1, 1)

    monkeypatch.setattr(bot, "search", fake_search)
    obs = observation(FowBoard(), chess.WHITE)
    for _ in range(3):
        agent.observe(obs)   # the same view three times, as when both sides shuffle
        agent.act(100.0)
    assert seen[0] is None
    assert seen[1]["g1f3"] == 1 and seen[2]["g1f3"] == 2
    assert sum(seen[2].values()) == 2


def test_reaching_the_same_squares_by_another_move_counts_as_a_repeat(monkeypatch) -> None:
    """In an arena game a rook came to d5 three times by three different moves and the
    game was drawn 13 points ahead: what is counted is where our pieces end up."""
    agent = make_agent()
    seen = []

    def fake_search(states, moves, side, budget, rng, repeat_counts=None):
        seen.append({} if repeat_counts is None else dict(zip([m.uci() for m in moves], repeat_counts)))
        return SearchResult(next(m for m in moves if m.uci() in ("c5d5", "d4d5", "d6d5")), 0.5, 0.0, 1, 1)

    monkeypatch.setattr(bot, "search", fake_search)
    monkeypatch.setattr(agent.belief, "observe", lambda obs, own_move=None, policy=None: None)
    for fen in ("7k/8/8/2R5/8/8/8/K7 w - - 0 1", "7k/8/8/8/3R4/8/8/K7 w - - 0 1", "7k/8/3R4/8/8/8/8/K7 w - - 0 1"):
        agent.observe(observation(FowBoard(fen), chess.WHITE))
        agent.last_move = None   # the rook is somewhere else each time: this is not a real game
        agent.act(100.0)
    assert seen[0].get("c5d5", 0) == 0
    assert seen[1]["d4d5"] == 1 and seen[1]["d4d6"] == 0   # back where it stood, by another road
    assert seen[2]["d6d5"] == 2


class StubPool:
    """Stands in for the engine pool; the Stockfish search itself is patched per test."""

    def __init__(self, ready: int = 2, restarts: int = 0):
        self.ready, self.restarts, self.restart_limit, self.failure = ready, restarts, 3, "stub"
        self.closed = False
        self.deaths = 0
        self.allowances: list[float] = []  # seconds each restart was given

    def ready_count(self) -> int:
        return self.ready

    def restart(self, deadline: float) -> int:
        self.restarts += 1
        self.allowances.append(deadline - time.monotonic())
        return 0

    def close(self) -> None:
        self.closed = True


def test_stockfish_move_is_played_when_the_engine_answers(monkeypatch) -> None:
    from fow.obscuro.stockfish_search import StockfishResult
    agent = make_agent(move_time=0.3)
    agent.pool = StubPool()
    seen = {}

    def fake_stockfish(pool, states, moves, side, budget, rng, repeat_counts=None, weights=None):
        seen["budget"] = budget
        return StockfishResult(chess.Move.from_uci("g1f3"), 0.1, 0.0, 1, 1, 1, (5, 5), False,
                               tuple(0.0 for _ in moves), tuple(0.0 for _ in moves))

    monkeypatch.setattr(bot, "stockfish_search", fake_stockfish)
    monkeypatch.setattr(bot, "search", boom)  # the PCFR+ search must not be needed
    agent.observe(observation(FowBoard(), chess.WHITE))
    assert agent.act(100.0) == "g1f3"
    assert 0.25 < seen["budget"] <= 0.3 and agent.fallbacks == 0


@pytest.mark.parametrize("stockfish_outcome", ["returns nothing", "raises"])
def test_pcfr_search_takes_over_when_stockfish_cannot_answer(monkeypatch, stockfish_outcome) -> None:
    agent = make_agent(move_time=0.5)
    agent.pool = StubPool()
    monkeypatch.setattr(bot, "stockfish_search",
                        (lambda *a, **k: None) if stockfish_outcome == "returns nothing" else boom)
    seen = {}

    def fake_search(states, moves, side, budget, rng, repeat_counts=None):
        seen["budget"] = budget
        return SearchResult(chess.Move.from_uci("e2e4"), 0.0, 0.0, 1, 1)

    monkeypatch.setattr(bot, "search", fake_search)
    agent.observe(observation(FowBoard(), chess.WHITE))
    assert agent.act(100.0) == "e2e4"
    assert 0.4 < seen["budget"] <= 0.5  # it gets what is left of the move's time
    assert agent.pool is not None       # one bad move does not switch Stockfish off


def test_stockfish_is_dropped_for_the_game_once_restarts_run_out(monkeypatch) -> None:
    agent = make_agent(move_time=0.5)
    pool = agent.pool = StubPool(ready=0, restarts=3)
    monkeypatch.setattr(bot, "stockfish_search", boom)  # must not be called without engines
    play(agent, 4)
    assert agent.pool is None and pool.closed and agent.fallbacks == 0


def test_dead_engines_are_restarted_within_half_the_move(monkeypatch) -> None:
    agent = make_agent(move_time=0.5)
    agent.engine_start_seconds = 0.1  # what starting them took at the beginning of the game
    pool = agent.pool = StubPool(ready=1, restarts=1)
    monkeypatch.setattr(bot, "stockfish_search", lambda *a, **k: None)
    agent.observe(observation(FowBoard(), chess.WHITE))
    assert agent.act(100.0) is not None
    assert pool.restarts == 2 and len(pool.allowances) == 1  # one attempt this move
    assert 0.2 < pool.allowances[0] <= 0.25                  # half of the 0.5 s, no more


def test_no_restart_is_spent_when_the_move_cannot_afford_one(monkeypatch) -> None:
    agent = make_agent(move_time=0.5)
    agent.engine_start_seconds = 0.4  # a restart would need about 0.6 s; half the move is 0.25 s
    pool = agent.pool = StubPool(ready=1, restarts=1)
    monkeypatch.setattr(bot, "stockfish_search", lambda *a, **k: None)
    agent.observe(observation(FowBoard(), chess.WHITE))
    assert agent.act(100.0) is not None
    assert pool.restarts == 1 and pool.allowances == []


def test_late_stockfish_failure_plays_a_fallback_move_and_says_so(monkeypatch, capsys) -> None:
    """Clock-based budget: if Stockfish uses the move's time and returns nothing, there is
    no time for the PCFR+ search either. The log must say what was actually played."""
    agent = make_agent(move_time=None)
    agent.pool = StubPool()

    def slow_and_empty(pool, states, moves, side, budget, rng, repeat_counts=None, weights=None):
        time.sleep(budget - 0.05)
        return None

    monkeypatch.setattr(bot, "stockfish_search", slow_and_empty)
    monkeypatch.setattr(bot, "search", boom)  # must not be called with 0.05 s
    monkeypatch.setattr(bot, "move_budget", lambda remaining, increment: 0.3)
    agent.observe(observation(FowBoard(), chess.WHITE))
    assert agent.act(100.0) is not None and agent.fallbacks == 1
    logged = capsys.readouterr().err
    assert "no stockfish result" in logged and "playing a fallback move" in logged
    assert "PCFR+ search with" not in logged


def test_engine_loss_is_logged_with_its_reason(monkeypatch, capsys) -> None:
    from fow.obscuro.stockfish_search import StockfishResult
    agent = make_agent(move_time=0.3)
    pool = agent.pool = StubPool()

    def loses_an_engine(pool, states, moves, side, budget, rng, repeat_counts=None, weights=None):
        pool.deaths, pool.ready, pool.failure = 1, 1, "exited during a search; last output: boom"
        return StockfishResult(moves[0], 0.0, 0.0, 1, 1, 1, (3, 3), False,
                               tuple(0.0 for _ in moves), tuple(0.0 for _ in moves))

    monkeypatch.setattr(bot, "stockfish_search", loses_an_engine)
    agent.observe(observation(FowBoard(), chess.WHITE))
    agent.act(100.0)
    logged = capsys.readouterr().err
    assert "stockfish engine lost (exited during a search; last output: boom); 1 of 2 running" in logged
    assert " eng=1 " in logged


def test_engines_that_did_not_start_get_another_try_on_the_first_move(monkeypatch, tmp_path, capsys) -> None:
    """Nothing answered within the start-up time. The pool is kept, so the first move,
    which has time to spare, tries again instead of giving Stockfish up for the game."""
    fake = Path(__file__).with_name("fake_uci_engine.py")
    wrapper = tmp_path / "fakefish"
    wrapper.write_text(f'#!/bin/bash\nexec "{sys.executable}" "{fake}"\n')
    wrapper.chmod(0o755)
    monkeypatch.setenv("FAKE_UCI", "mute")
    monkeypatch.setattr(bot, "ENGINE_START_SECONDS", 0.3)
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=2.0, engine=wrapper)
    try:
        agent.reset(chess.WHITE, 180, 2)
        assert agent.pool is not None and agent.pool.ready_count() == 0
        assert "stockfish did not start" in capsys.readouterr().err
        monkeypatch.setenv("FAKE_UCI", "")   # whatever kept them silent has passed
        agent.observe(observation(FowBoard(), chess.WHITE))
        assert agent.act(100.0) is not None
        logged = capsys.readouterr().err
        assert "restarted stockfish: 2 started" in logged and "obscuro: sf " in logged
        assert agent.pool.ready_count() == 2 and 0 < agent.engine_start_seconds < 1.0
    finally:
        agent.close()


def test_the_ready_line_names_the_binary_and_says_what_is_missing(monkeypatch, tmp_path, capsys) -> None:
    fake = Path(__file__).with_name("fake_uci_engine.py")
    wrapper = tmp_path / "fakefish"
    wrapper.write_text(f'#!/bin/bash\nexec "{sys.executable}" "{fake}"\n')
    wrapper.chmod(0o755)
    monkeypatch.setenv("FAKE_UCI", f"mute_one={tmp_path / 'silent'}")
    monkeypatch.setattr(bot, "ENGINE_START_SECONDS", 1.0)
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=0.3, engine=wrapper)
    try:
        agent.reset(chess.WHITE, 180, 2)
        logged = capsys.readouterr().err
        assert f"stockfish ready: 1 of 2 engines in 1.0" in logged
        assert f"binary {wrapper}" in logged and "missing: no uciok in time" in logged
        # What the engine that works needed, not the second we waited for the silent one:
        # otherwise a restart would never look affordable again.
        assert 0 < agent.engine_start_seconds < 0.8
    finally:
        agent.close()


def test_reset_and_close_stop_the_engines() -> None:
    agent = make_agent()
    first = agent.pool = StubPool()
    agent.reset(chess.BLACK, 180, 2)
    assert first.closed and agent.pool is None  # no engine configured in these tests
    second = agent.pool = StubPool()
    agent.close()
    agent.close()
    assert second.closed and agent.pool is None


# ---------------------------------------------------------------------------------------
# The set of positions kept by the compiled helper.

def helped_agent(helper: str, move_time: float | None = 0.05) -> "bot.ObscuroAgent":
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=move_time, positions=Path(helper))
    agent.reset(chess.WHITE, 180, 2)
    return agent


def test_the_bot_keeps_its_set_in_the_helper_when_it_has_one(helper, capsys) -> None:
    from fow.obscuro.position_set import MAX_STATES, PositionSet
    agent = helped_agent(helper)
    try:
        assert isinstance(agent.belief, PositionSet) and agent.belief.fallback is None
        assert agent.belief_ceiling == MAX_STATES and agent.belief.max_states == MAX_STATES
        assert "position-set helper ready" in capsys.readouterr().err
        board = play(agent, 24)
        if board.turn == chess.WHITE:                    # not if the game ended early
            agent.observe(observation(board, chess.WHITE))   # the last reply, which play() leaves unseen
        assert agent.belief.fallback is None and agent.fallbacks == 0 and agent.belief_ok
        # The set is complete, so the true position is in it: among the states Python sees
        # whenever it sees them all.
        assert agent.belief.exact
        if len(agent.belief) == len(agent.belief.states):
            assert any(state.board_fen() == board.board_fen() for state in agent.belief.states)
        assert agent._belief_size().split()[0].rstrip("~").isdigit()   # no "/cap": the ceiling is not lowered
        process = agent.belief.helper.proc
    finally:
        agent.close()
    assert process.poll() is not None                # the helper is stopped with the bot
    agent.reset(chess.BLACK, 180, 2)                 # and a new game starts a new one
    try:
        assert isinstance(agent.belief, PositionSet) and agent.belief.helper.proc is not process
    finally:
        agent.close()


def test_without_a_helper_the_set_is_kept_in_python(tmp_path, capsys) -> None:
    from fow.obscuro.belief import Belief
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=0.05, positions=tmp_path / "missing")
    agent.reset(chess.WHITE, 180, 2)
    assert isinstance(agent.belief, Belief) and agent.belief_ceiling == 200
    assert "no position-set helper at" in capsys.readouterr().err
    agent = make_agent()                             # none asked for: nothing to report
    assert isinstance(agent.belief, Belief) and "position-set" not in capsys.readouterr().err
    not_a_helper = tmp_path / "broken"
    not_a_helper.write_text("#!/bin/sh\nexit 3\n")
    not_a_helper.chmod(0o755)
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=0.05, positions=not_a_helper)
    agent.reset(chess.WHITE, 180, 2)
    assert isinstance(agent.belief, Belief)
    assert "the position-set helper did not start" in capsys.readouterr().err
    play(agent, 6)


def test_a_helper_lost_in_mid_game_is_reported_once_and_the_game_goes_on(helper, capsys) -> None:
    agent = helped_agent(helper)
    try:
        def kill_at_move_four(agent, board):
            if board.fullmove_number == 4:
                agent.belief.helper.proc.kill()
                agent.belief.helper.proc.wait(timeout=5)

        play(agent, 20, on_turn=kill_at_move_four)
        log_text = capsys.readouterr().err
        assert log_text.count("position-set helper lost") == 1 and "carrying on in Python" in log_text
        assert agent.belief.fallback is not None and agent.belief_ok and agent.fallbacks == 0
        assert agent.belief_ceiling == 200           # the Python belief's cap, from here on
    finally:
        agent.close()


def test_giving_up_on_stockfish_leaves_the_helper_running(helper, monkeypatch, capsys) -> None:
    from fow.obscuro.position_set import PositionSet
    agent = helped_agent(helper, move_time=0.5)
    try:
        pool = agent.pool = StubPool(ready=0, restarts=3)
        monkeypatch.setattr(bot, "stockfish_search", boom)  # must not be called without engines
        play(agent, 8)
        assert agent.pool is None and pool.closed
        # Only the engines are gone. The set is still the helper's, and still complete.
        assert isinstance(agent.belief, PositionSet) and agent.belief.fallback is None
        assert agent.belief.helper.proc.poll() is None and agent.belief.exact
        assert "position-set helper lost" not in capsys.readouterr().err
    finally:
        agent.close()


def test_the_helper_is_told_how_long_an_update_may_take(helper) -> None:
    agent = helped_agent(helper, move_time=None)
    try:
        agent.observe(observation(FowBoard(), chess.WHITE))
        agent.act(60.0)
        assert agent.belief.allowance == pytest.approx(bot.BELIEF_SHARE * agent.move_seconds)
        assert 0 < agent.belief.allowance < 0.5 * agent.move_seconds
    finally:
        agent.close()
