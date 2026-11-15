"""The uploaded versions kept as bots/<name>_v<N> stay as they were frozen.

Each is a record of what played in the arena and a fixed opponent for the working bot, so
it must not change and must not run the working bot's code. docs/versions.md says how a
version is frozen.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "tests" / "frozen_bots.sha256"  # Each line is "<sha256>  <path>", as shasum prints it.
# A local build leaves these in a bot folder, and .gitignore keeps them out of the repository.
BUILT = {"stockfish", "stockfish.new", ".build-tmp", "positions"}
ANYWHERE = {"__pycache__", ".DS_Store"}
FOLDERS = [folder for folder in sorted((ROOT / "bots").iterdir())
           if folder.is_dir() and re.fullmatch(r".+_v\d+", folder.name)]


def frozen_files() -> list[Path]:
    """The files of every bots/<name>_v<N> folder, without what a local build leaves there."""
    found = []
    for folder in FOLDERS:
        for path in sorted(folder.rglob("*")):
            parts = path.relative_to(folder).parts
            if path.is_file() and parts[0] not in BUILT and not ANYWHERE & set(parts):
                found.append(path)
    return found


def test_frozen_bots_are_unchanged() -> None:
    recorded = {name: digest for digest, name in
                (line.split() for line in RECORD.read_text().splitlines() if line.strip())}
    found = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in frozen_files()}
    changed = sorted(name for name in found.keys() & recorded.keys() if found[name] != recorded[name])
    appeared = sorted(found.keys() - recorded.keys())
    missing = sorted(recorded.keys() - found.keys())
    assert not (changed or appeared or missing), (
        f"Frozen files differ from tests/frozen_bots.sha256. Changed: {changed}. Not in the "
        f"record: {appeared}. Missing: {missing}. Every folder named bots/<name>_v<N> is a "
        "frozen version and is never edited. Undo the change and work in bots/obscuro and "
        "fow/obscuro. docs/versions.md says how a new version is frozen.")


def test_frozen_bots_do_not_name_the_working_package() -> None:
    """This also covers the build scripts, which load engine.py by its path."""
    stray = [path.relative_to(ROOT).as_posix() for path in frozen_files()
             if re.search(rb"fow[./]obscuro", path.read_bytes())]
    assert not stray, f"{stray} name the working bot's package, fow.obscuro"


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda folder: folder.name)
def test_a_frozen_bot_loads_only_its_own_code(folder: Path) -> None:
    """A frozen bot that imported fow.obscuro would play the working bot's code without any error."""
    listing = "import sys; sys.path.insert(0, ''); import bot; " \
              "print(sorted(name for name in sys.modules if name.startswith('fow.obscuro')))"
    ran = subprocess.run([sys.executable, "-B", "-c", listing], cwd=folder, capture_output=True,
                         text=True, timeout=60)
    assert ran.returncode == 0, ran.stderr[-2000:]
    assert ran.stdout.strip() == "[]", f"{folder.name} loaded the working bot's modules: {ran.stdout}"
