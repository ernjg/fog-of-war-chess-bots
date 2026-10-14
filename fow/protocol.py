"""stdin/stdout protocol loop for the Fog of War arena.

``run(agent)`` owns stdout. The only lines it ever writes there are ``ready``
and ``move <uci>``; everything else (including stray ``print`` calls inside
the agent) is redirected to stderr. See starter/README.md for the protocol.
"""
from __future__ import annotations

import re
import sys
import traceback
from typing import TextIO

OBSERVATION_CHARACTERS = frozenset("?-PNBRQKpnbrqk")
UCI_PATTERN = re.compile(r"[a-h][1-8][a-h][1-8][qrbn]?")


def log(*parts: object) -> None:
    """Diagnostics go to stderr; stdout is reserved for the protocol."""
    print(*parts, file=sys.stderr, flush=True)


class Agent:
    """Interface a bot implements. All methods are called from ``run``."""

    def reset(self, color: bool, base: float, inc: float) -> None:
        """Start a new game. ``color`` is True for White (python-chess convention)."""

    def observe(self, obs: str) -> None:
        """Receive a 64-character observation (a1..h8). Called before every ply."""

    def act(self, remaining_time: float) -> str | None:
        """Return the move to play in UCI, or None if there is no legal move."""
        raise NotImplementedError


def is_observation(line: str) -> bool:
    return len(line) == 64 and set(line) <= OBSERVATION_CHARACTERS


def run(agent: Agent, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
    """Drive ``agent`` over the arena protocol until stdin closes."""
    stdin = sys.stdin if stdin is None else stdin
    out = sys.stdout if stdout is None else stdout
    # Anything the agent prints from now on lands on stderr, never on the wire.
    sys.stdout = sys.stderr

    def emit(line: str) -> None:
        out.write(line + "\n")
        out.flush()

    try:
        if stdin.readline().strip().lower() != "fow":
            log("protocol: expected 'fow' header, exiting")
            return
        header = stdin.readline().split()
        if len(header) != 3 or header[0].lower() not in ("w", "b"):
            log("protocol: malformed color/time header, exiting:", header)
            return
        color = header[0].lower() == "w"
        base, inc = float(header[1]), float(header[2])
        agent.reset(color, base, inc)
        emit("ready")

        for raw in stdin:
            line = raw.strip()
            if is_observation(line):
                agent.observe(line)
                continue
            try:
                remaining = float(line)
            except ValueError:
                log("protocol: ignoring unexpected input line:", line[:80])
                continue
            uci = agent.act(remaining)
            if uci is None:
                log("protocol: agent has no move, exiting")
                return
            if not UCI_PATTERN.fullmatch(uci):
                log("protocol: agent returned malformed UCI, exiting:", uci)
                return
            emit("move " + uci)
    except Exception:
        # Tracebacks must never reach stdout. Exiting forfeits, but cleanly.
        log("protocol: unhandled exception")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
