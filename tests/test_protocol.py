"""Play a full game against each bot process and check every stdout line."""
from __future__ import annotations

import os
import random
import re
import select
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402
import referee  # noqa: E402

MOVE_LINE = re.compile(r"move [a-h][1-8][a-h][1-8][qrbn]?")
READ_TIMEOUT = 15.0


def read_line(proc: subprocess.Popen) -> str:
    ready, _, _ = select.select([proc.stdout], [], [], READ_TIMEOUT)
    assert ready, "bot produced no output within the timeout"
    line = proc.stdout.readline()
    assert line, "bot closed stdout"
    return line.rstrip("\n")


OBSCURO = ["--max-states", "300", "--move-time"]
STOCKFISH = os.environ.get("FOW_STOCKFISH", "")
FAKE_ENGINE = Path(__file__).with_name("fake_uci_engine.py")

# name -> (bot folder, arguments, engine faults or None, texts its stderr must contain;
#          a tuple of texts means any one of them)
CASES = {
    "random": ("random", [], None, []),
    "greedy": ("greedy", [], None, []),
    "obscuro": ("obscuro", [*OBSCURO, "0.05", "--stockfish", "off"], None,
                ["stockfish is switched off"]),
    "obscuro, no engine built": ("obscuro", [*OBSCURO, "0.05", "--stockfish", "no/such/binary"],
                                 None, ["no stockfish at"]),
    "obscuro with an engine": ("obscuro", [*OBSCURO, "0.3"], "",
                               ["stockfish ready: 2 of 2 engines", "obscuro: sf "]),
    # Each engine answers one position and exits; so does every replacement. Whether the
    # bot replaces them depends on how fast they started (it does not spend a restart it
    # cannot afford), so either ending is right: restarts used up, or none attempted.
    "obscuro, engines keep dying": ("obscuro", [*OBSCURO, "1.0"], "die_at=3",
                                    ["stockfish engine lost (exited",
                                     ("stockfish is gone for this game",
                                      "no stockfish result (0 engines running)"),
                                     "obscuro: PCFR+ search with the"]),
    "obscuro, engine never answers": ("obscuro", [*OBSCURO, "0.3"], "mute",
                                      ["stockfish did not start"]),
    "obscuro with stockfish": ("obscuro", [*OBSCURO, "0.3", "--stockfish", STOCKFISH], None,
                               ["stockfish ready: 2 of 2 engines", "obscuro: sf "]),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_full_game_stdout_is_protocol_only(case: str, tmp_path: Path) -> None:
    bot, args, faults, expected_log = CASES[case]
    if case == "obscuro with stockfish" and not Path(STOCKFISH).is_file():
        pytest.skip("FOW_STOCKFISH is not a Stockfish binary")
    env = dict(os.environ, PYTHON=sys.executable)
    env.pop("FOW_STOCKFISH", None)  # each case names its own engine
    if faults is not None:  # a scripted engine, started through a wrapper the bot can execute
        wrapper = tmp_path / "fakefish"
        wrapper.write_text(f'#!/bin/bash\nexec "{sys.executable}" "{FAKE_ENGINE}"\n')
        wrapper.chmod(0o755)
        args = [*args, "--stockfish", str(wrapper)]
        env["FAKE_UCI"] = faults
    log_path = tmp_path / "stderr.txt"
    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(["bash", str(ROOT / "bots" / bot / "run.sh"), "--seed", "7", *args],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log_file,
                                text=True, bufsize=1, env=env)
    stdout_lines: list[str] = []
    side = chess.WHITE
    rng = random.Random(1)
    try:
        proc.stdin.write("fow\nw 180 2\n")
        proc.stdin.flush()
        stdout_lines.append(read_line(proc))
        assert stdout_lines[-1] == "ready"

        board = referee.FowBoard()
        repetitions = Counter({referee.position_key(board): 1})
        while referee.outcome(board, repetitions) is None and len(board.move_stack) < 1000:
            proc.stdin.write(referee.observation(board, side) + "\n")
            proc.stdin.flush()
            if board.turn == side:
                proc.stdin.write("100.0\n")
                proc.stdin.flush()
                line = read_line(proc)
                stdout_lines.append(line)
                assert MOVE_LINE.fullmatch(line), f"bad stdout line: {line!r}"
                move = chess.Move.from_uci(line[5:])
                assert move in referee.fow_moves(board), f"illegal move {move}"
            else:
                move = rng.choice(list(referee.fow_moves(board)))
            board.push(move)
            repetitions[referee.position_key(board)] += 1
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)
        extra = proc.stdout.read()
    stdout_lines.extend(extra.splitlines())
    assert len(stdout_lines) > 1, "no moves were played"
    bad = [l for l in stdout_lines if l != "ready" and not MOVE_LINE.fullmatch(l)]
    assert not bad, f"non-protocol stdout lines: {bad}"
    log_text = log_path.read_text()
    for text in expected_log:
        any_of = text if isinstance(text, tuple) else (text,)
        assert any(one in log_text for one in any_of), f"{text!r} missing from stderr:\n{log_text[-2000:]}"
    assert "Traceback" not in log_text, log_text[-3000:]
