"""Shared fixtures."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
POSITIONS_SOURCE = ROOT / "bots" / "obscuro" / "positions.cpp"
MAC_SDK = "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"


def build_helper(tmp_path_factory, source: Path, name: str) -> str:
    compiler = os.environ.get("CXX") or next((c for c in ("g++", "c++", "clang++") if shutil.which(c)), None)
    if compiler is None:
        pytest.skip("no C++ compiler")
    env = dict(os.environ)
    if sys.platform == "darwin" and "SDKROOT" not in env and Path(MAC_SDK).is_dir():
        env["SDKROOT"] = MAC_SDK  # some Macs' linkers do not find the SDK on their own
    binary = tmp_path_factory.mktemp(name) / "positions"
    built = subprocess.run([compiler, "-O2", "-std=c++17", "-o", str(binary), str(source)],
                           capture_output=True, text=True, env=env, timeout=300)
    assert built.returncode == 0, built.stderr[-2000:]
    return str(binary)


@pytest.fixture(scope="session")
def helper(tmp_path_factory) -> str:
    """The position-set helper, built once with the system's C++ compiler; tests that
    need it are skipped where there is none."""
    return build_helper(tmp_path_factory, POSITIONS_SOURCE, "positions")


@pytest.fixture(scope="session")
def helper_ebotI(tmp_path_factory) -> str:
    """eBotI's helper, which also carries the game tree (tree.inc)."""
    return build_helper(tmp_path_factory, ROOT / "bots" / "eBotI" / "positions.cpp", "positions_ebotI")
