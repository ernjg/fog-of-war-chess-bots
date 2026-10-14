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


@pytest.mark.parametrize("bot", ["random", "greedy"])
def test_full_game_stdout_is_protocol_only(bot: str) -> None:
    env = dict(os.environ, PYTHON=sys.executable)
    proc = subprocess.Popen(["bash", str(ROOT / "bots" / bot / "run.sh"), "--seed", "7"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, bufsize=1, env=env)
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
