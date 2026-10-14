"""Helpers for running bots locally with the starter referee.

Local tools run bots through their ``run.sh`` with ``PYTHON`` pointing at the
project interpreter, exactly as the arena does with ``python3``.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import fow  # noqa: F401  (puts the starter kit on sys.path)
import referee

ROOT = Path(__file__).resolve().parent.parent
BOTS_DIR = ROOT / "bots"


def bot_argv(spec: str, *extra: str) -> list[str]:
    """Resolve a bot name (``greedy``), a bot directory, or a run.sh path."""
    path = Path(spec)
    if not path.exists():
        path = BOTS_DIR / spec
    if path.is_dir():
        path = path / "run.sh"
    if not path.is_file():
        raise FileNotFoundError(f"No bot at {spec!r} (expected bots/<name>/run.sh or a run.sh path)")
    return ["bash", str(path.resolve()), *extra]


def use_project_python() -> None:
    os.environ["PYTHON"] = sys.executable


class PauseControl:
    """Freeze a bot's whole process group on the opponent's turn, like the arena.

    ``referee.run_match`` calls ``freeze()`` after ``ready`` and after each move,
    and ``resume()`` right before the bot's next clock prompt.
    """

    def __init__(self, proc: subprocess.Popen):
        self.proc = proc

    def freeze(self) -> None:
        self._signal(signal.SIGSTOP)

    def resume(self) -> None:
        self._signal(signal.SIGCONT)

    def _signal(self, sig: int) -> None:
        try:
            os.killpg(self.proc.pid, sig)  # referee starts each bot in its own session
        except (ProcessLookupError, PermissionError):
            pass  # already exited; the referee reports that as the bot's failure


class _RecordingSubprocess:
    """Stand-in for the ``subprocess`` module inside ``referee`` that remembers
    the most recent ``Popen``. The referee's ``turn_control_factory`` receives
    only a ready-file path, not the process, so this is how we find it."""

    def __init__(self):
        self.latest: subprocess.Popen | None = None

    def __getattr__(self, name):
        return getattr(subprocess, name)

    def Popen(self, *args, **kwargs):
        self.latest = subprocess.Popen(*args, **kwargs)
        return self.latest


_recorder = _RecordingSubprocess()


def pause_control_factory(_ready_file=None) -> PauseControl:
    if referee.subprocess is not _recorder:
        referee.subprocess = _recorder
    if _recorder.latest is None:
        raise RuntimeError("pause_control_factory called before the referee started a bot")
    return PauseControl(_recorder.latest)


def install_pausing() -> None:
    """Make every bot the referee starts pausable via ``pause_control_factory``."""
    referee.subprocess = _recorder
