"""Shared library for our Fog of War chess bots.

Importing this package makes the starter kit's ``referee.py`` (rules) and
``uniform_random.py`` (``ObservationTracker``) importable. It looks for them
next to the ``fow/`` directory first (the flat layout of a packaged bot) and
then in ``<repo>/starter/`` (the development layout). We never reimplement
the rules; the starter files are the source of truth.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_PARENT = Path(__file__).resolve().parent.parent


def _locate_starter() -> Path:
    for candidate in (_PACKAGE_PARENT, _PACKAGE_PARENT / "starter"):
        if (candidate / "referee.py").is_file() and (candidate / "uniform_random.py").is_file():
            return candidate
    raise ImportError(
        "Could not find the starter's referee.py and uniform_random.py next to "
        f"fow/ or in {_PACKAGE_PARENT / 'starter'}"
    )


STARTER_DIR = _locate_starter()
if str(STARTER_DIR) not in sys.path:
    sys.path.insert(0, str(STARTER_DIR))
