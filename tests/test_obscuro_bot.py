"""The obscuro bot charges belief time to its budget and survives internal errors."""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402
from referee import FowBoard, fow_moves, observation  # noqa: E402

_spec = importlib.util.spec_from_file_location("obscuro_bot", ROOT / "bots" / "obscuro" / "bot.py")
bot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bot)


def make_agent(move_time: float | None = 0.05) -> "bot.ObscuroAgent":
    agent = bot.ObscuroAgent(seed=1, max_states=200, move_time=move_time)
    agent.reset(chess.WHITE, 180, 2)
    return agent


def play(agent, plies: int, on_turn=None) -> FowBoard:
    """Drive ``agent`` as White against random replies; every move must be FoW-legal."""
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
            move = rng.choice(safe)
        board.push(move)
    return board


def boom(*args, **kwargs):
    raise RuntimeError("boom")


def test_belief_time_is_subtracted_from_the_budget(monkeypatch) -> None:
    agent = make_agent(move_time=None)
    seen = {}

    def fake_search(states, moves, side, budget, rng):
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
    monkeypatch.setattr(bot, "project", boom)
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
