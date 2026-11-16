"""bots/obscuro/build.sh, run on small stand-ins for the Stockfish source tree.

Whatever is wrong with the tree, the script has to exit 0 with a last line saying that
Stockfish was not built, so that the arena still accepts the upload; with the
REQUIRE_STOCKFISH marker it has to exit 1 instead. A stand-in that compiles into a working
engine checks the other direction: the binary is kept and the last line says OK.

The Linux branch of the script (the g++ commands, and what happens when the compile or the
binary fails) is run with stand-ins for uname, g++ and timeout, so it is exercised on any
machine; what the stand-ins cannot show is whether the real g++ accepts the flags. The
real build is not run here (it takes the Stockfish source and a quarter of a minute);
docs/obscuro.md says how to rehearse it.
"""
from __future__ import annotations

import functools
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bots" / "obscuro" / "build.sh"
ENGINE_MODULE = ROOT / "fow" / "obscuro" / "engine.py"
NET = "nn-0123456789ab.nnue"
NOT_BUILT = "build: STOCKFISH NOT BUILT: "
BUILT = "build: STOCKFISH OK: "
POSITIONS_SOURCE = ROOT / "bots" / "obscuro" / "positions.cpp"
SET_BUILT = "build: POSITION SET OK: "
SET_NOT_BUILT = "build: POSITION SET NOT BUILT: "

# Enough of a UCI engine for the bot's start-up check: the handshake, and all twenty moves
# of the starting position scored.
WORKING_ENGINE = r"""
#include <iostream>
#include <string>
int main() {
    const char* moves[] = {"a2a3", "a2a4", "b2b3", "b2b4", "c2c3", "c2c4", "d2d3", "d2d4", "e2e3",
                           "e2e4", "f2f3", "f2f4", "g2g3", "g2g4", "h2h3", "h2h4", "b1a3", "b1c3",
                           "g1f3", "g1h3"};
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line == "uci") std::cout << "uciok" << std::endl;
        else if (line == "isready") std::cout << "readyok" << std::endl;
        else if (line.rfind("go", 0) == 0) {
            for (int i = 0; i < 20; ++i)
                std::cout << "info depth 1 seldepth 1 multipv " << i + 1 << " score cp " << 20 - i
                          << " nodes 1 nps 1 hashfull 0 tbhits 0 time 1 pv " << moves[i] << "\n";
            std::cout << "bestmove a2a3" << std::endl;
        } else if (line == "quit") break;
    }
    return 0;
}
"""
SILENT_ENGINE = "int main() { return 1; }\n"      # compiles, and exits without a word
BROKEN_SOURCE = "int main( { this does not compile\n"


@functools.cache
def compiler_works() -> bool:
    """Whether the compiler build.sh uses on this machine can build a program here."""
    name = {("Darwin", "arm64"): "clang++", ("Linux", "x86_64"): "g++"}.get(
        (platform.system(), platform.machine()))
    if name is None or shutil.which(name) is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "main.cpp").write_text("int main() { return 0; }\n")
        return subprocess.run([name, "-o", "main", "main.cpp"], cwd=tmp,
                              capture_output=True).returncode == 0


def needs_compiler() -> None:
    if not compiler_works():
        pytest.skip("no working C++ compiler for build.sh here (on macOS, SDKROOT may need to "
                    "point at the SDK)")


def tree(root: Path, source: str | None = None, *, net: bool = True, marker: bool = False,
         engine_module: bool = True) -> Path:
    """A copy of build.sh in the packaged layout, with a one-file "Stockfish" beside it."""
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT, root / "build.sh")
    if marker:
        (root / "REQUIRE_STOCKFISH").touch()
    if engine_module:
        (root / "fow" / "obscuro").mkdir(parents=True)
        shutil.copy2(ENGINE_MODULE, root / "fow" / "obscuro" / "engine.py")
    if source is not None:
        src = root / "stockfish" / "src"
        src.mkdir(parents=True)
        (src / "evaluate.h").write_text(f'#define EvalFileDefaultName "{NET}"\n')
        (src / "main.cpp").write_text(source)
        (src / "Makefile").write_text("SRCS = main.cpp\n")
        if net:
            (src / NET).write_text("not a network\n")
    return root


def build(root: Path, **env: str) -> tuple[int, list[str]]:
    result = subprocess.run(["bash", str(root / "build.sh")], capture_output=True, text=True,
                            timeout=120, env={**os.environ, "PYTHON": sys.executable, **env})
    return result.returncode, result.stdout.strip().splitlines()


def leftovers(root: Path) -> list[str]:
    """What a build must not leave in the upload: its scratch folder and object files."""
    return sorted(str(path.relative_to(root)) for path in root.rglob("*")
                  if path.name == ".build-tmp" or path.suffix == ".o" or path.name == ".depend")


def test_no_source_is_reported_and_the_upload_is_still_accepted(tmp_path: Path) -> None:
    status, lines = build(tree(tmp_path))
    assert status == 0 and lines[-1].startswith(NOT_BUILT + "no source in stockfish/src")
    assert all(line.startswith("build: ") for line in lines)
    assert leftovers(tmp_path) == []


def test_the_marker_rejects_an_upload_without_stockfish(tmp_path: Path) -> None:
    status, lines = build(tree(tmp_path, marker=True))
    assert status == 1 and lines[-1].startswith(NOT_BUILT + "no source in stockfish/src")
    assert "REQUIRE_STOCKFISH" in lines[-2]


def test_missing_network_file_is_reported(tmp_path: Path) -> None:
    status, lines = build(tree(tmp_path, WORKING_ENGINE, net=False))
    assert status == 0 and lines[-1] == NOT_BUILT + f"the network file {NET} is not in stockfish/src"
    assert not (tmp_path / "stockfish" / "src" / "stockfish").exists()


def test_source_that_does_not_compile_is_reported(tmp_path: Path) -> None:
    root = tree(tmp_path / "plain", BROKEN_SOURCE)
    status, lines = build(root)
    assert status == 0 and lines[-1].startswith(NOT_BUILT)
    assert not (root / "stockfish" / "src" / "stockfish").exists()
    assert leftovers(root) == []
    status, lines = build(tree(tmp_path / "strict", BROKEN_SOURCE, marker=True))
    assert status == 1 and lines[-1].startswith(NOT_BUILT)


def test_a_binary_the_bot_cannot_use_is_removed(tmp_path: Path) -> None:
    needs_compiler()
    status, lines = build(tree(tmp_path, SILENT_ENGINE))
    assert status == 0 and lines[-1].startswith(NOT_BUILT)
    assert "could not use the binary: 0 of 2 engines ready" in lines[-1]
    assert not (tmp_path / "stockfish" / "src" / "stockfish").exists()
    assert leftovers(tmp_path) == []


def test_a_working_engine_is_kept_and_passes_even_with_the_marker(tmp_path: Path) -> None:
    needs_compiler()
    status, lines = build(tree(tmp_path, WORKING_ENGINE, marker=True))
    assert status == 0, lines
    assert lines[-1].startswith(BUILT)
    assert "2 of 2 engines ready" in lines[-1] and "20 of 20 opening moves scored" in lines[-1]
    assert not any("so this build fails" in line for line in lines)
    binary = tmp_path / "stockfish" / "src" / "stockfish"
    assert binary.is_file() and os.access(binary, os.X_OK)
    assert leftovers(tmp_path) == []


def test_a_binary_that_came_with_the_upload_is_not_trusted(tmp_path: Path) -> None:
    """A binary built on another machine must never survive: it is deleted before anything
    else, so even a build that ends before it has tried anything (here: no network file)
    cannot leave it for the bot to find."""
    for name, source, net in (("ends early", WORKING_ENGINE, False), ("fails later", BROKEN_SOURCE, True)):
        root = tree(tmp_path / name, source, net=net)
        stale = root / "stockfish" / "src" / "stockfish"
        stale.write_text("#!/bin/sh\necho built somewhere else\n")
        stale.chmod(0o755)
        (root / "stockfish" / "src" / "old.o").write_text("stale object\n")
        status, lines = build(root)
        assert status == 0 and lines[-1].startswith(NOT_BUILT), name
        assert not stale.exists() and leftovers(root) == [], name


def test_a_binary_is_not_kept_when_the_start_up_check_cannot_run(tmp_path: Path) -> None:
    """Without the bot's engine code in the upload the check cannot run. The bot could not
    use the binary either, so it is reported as not built rather than trusted."""
    needs_compiler()
    status, lines = build(tree(tmp_path, WORKING_ENGINE, engine_module=False))
    assert status == 0 and lines[-1].startswith(NOT_BUILT + "the bot's own start-up check did not run")
    assert "engine.py is not in the upload" in lines[-1]
    assert not (tmp_path / "stockfish" / "src" / "stockfish").exists() and leftovers(tmp_path) == []


# ---------------------------------------------------------------------------------------
# The Linux branch, with stand-ins for the tools.

FAKE_ENGINE = Path(__file__).with_name("fake_uci_engine.py")
AVX2_CPU = "model name\t: Stand-in CPU\nflags\t\t: fpu sse sse2 ssse3 sse4_1 sse4_2 popcnt avx avx2 bmi1 bmi2\n"
NO_FLAGS = "model name\t: Hidden\n"

STUB_UNAME = """#!/bin/sh
case "$1" in
    -s) echo Linux ;;
    -m) echo x86_64 ;;
    *)  echo "Linux 6.1.0 x86_64" ;;
esac
"""
# "Compiles" by writing an object that remembers whether AVX2 was asked for, and "links" by
# writing a script that runs the scripted UCI engine, or one that exits at once.
STUB_GXX = """#!/bin/sh
[ "$1" = "--version" ] && { echo "g++ (stand-in) 12.2.0"; exit 0; }
echo "g++ $*" >> "$STUB_LOG"
[ -n "$STUB_GXX_FAILS" ] && { echo "main.cpp:1:1: error: stand-in failure" >&2; exit 1; }
out=""; compiling=0; kind=plain; previous=""
for arg in "$@"; do
    [ "$previous" = "-o" ] && out="$arg"
    [ "$arg" = "-c" ] && compiling=1
    [ "$arg" = "-mavx2" ] && kind=avx2
    previous="$arg"
done
if [ "$out" = positions ]; then   # the position-set helper: a program that passes or fails its self-test
    printf '#!/bin/sh\necho "selftest %s: stand-in"\n' "${STUB_SELFTEST:-ok}" > "$out"
    chmod +x "$out"
    exit 0
fi
if [ "$compiling" = 1 ]; then echo "$kind" > "$out"; exit 0; fi
if [ -n "$STUB_AVX2_DIES" ] && grep -q avx2 ./*.o; then
    printf '#!/bin/sh\nexit 132\n' > "$out"
else
    printf '#!/bin/sh\nexec "%s" "%s"\n' "$STUB_PYTHON" "$STUB_ENGINE" > "$out"
fi
chmod +x "$out"
"""
# `timeout -k 5 SECONDS command ...`, as the arena has it: the stand-in runs the command.
STUB_TIMEOUT = """#!/bin/sh
shift 3
exec "$@"
"""


def linux_tree(root: Path, cpuinfo: str, *, marker: bool = False) -> dict[str, str]:
    """A source tree of five files and the environment that makes build.sh take its Linux
    branch on it: stand-in tools first on PATH, and a CPU description of our choosing."""
    tree(root, "int main() { return 0; }\n", marker=marker)
    src = root / "stockfish" / "src"
    (src / "nnue").mkdir()
    for name, size in (("search.cpp", 400), ("uci.cpp", 200), ("misc.cpp", 100), ("nnue/network.cpp", 300)):
        (src / name).write_text("// stand-in\n" * size)
    (src / "Makefile").write_text("OBJS =\nSRCS = main.cpp search.cpp \\\n\tuci.cpp misc.cpp \\\n\tnnue/network.cpp\n")
    tools = root / "tools"
    tools.mkdir()
    for name, text in (("uname", STUB_UNAME), ("g++", STUB_GXX), ("timeout", STUB_TIMEOUT)):
        (tools / name).write_text(text)
        (tools / name).chmod(0o755)
    (root / "cpuinfo").write_text(cpuinfo)
    return {"PATH": f"{tools}{os.pathsep}{os.environ['PATH']}", "CPUINFO": str(root / "cpuinfo"),
            "STUB_LOG": str(root / "tools.log"), "STUB_PYTHON": sys.executable,
            "STUB_ENGINE": str(FAKE_ENGINE), "FAKE_UCI": "", "FAKE_UCI_SCORES": "{}"}


def commands(root: Path) -> list[str]:
    log = root / "tools.log"
    return log.read_text().splitlines() if log.exists() else []


def test_linux_build_compiles_every_file_once_for_avx2(tmp_path: Path) -> None:
    root = tmp_path / "avx2"
    status, lines = build(root, **linux_tree(root, AVX2_CPU, marker=True))
    assert status == 0, lines
    assert any("it has: avx2 bmi1 bmi2 popcnt sse4_1 ssse3" in line for line in lines)
    assert any("steps are cut off by: timeout" in line for line in lines)
    assert any("g++, ARCH=x86-64-avx2, 5 files, 3 at a time" in line for line in lines)
    assert lines[-1].startswith(BUILT + "ARCH=x86-64-avx2, ")
    assert "2 of 2 engines ready" in lines[-1] and "20 of 20 opening moves scored" in lines[-1]
    compiles = [line for line in commands(root) if " -c " in line]
    assert len(compiles) == 5 and {line.split()[-1] for line in compiles} == {
        "main.cpp", "search.cpp", "uci.cpp", "misc.cpp", "nnue/network.cpp"}  # each exactly once
    for flag in ("-std=c++17", "-O3", "-DNDEBUG", "-DIS_64BIT", "-DNNUE_EMBEDDING_OFF", "-DUSE_AVX2",
                 "-mavx2", "-mbmi", "-DUSE_SSE41", "-msse4.1", "-DUSE_POPCNT", "-mpopcnt",
                 "-DARCH=x86-64-avx2", "-fno-exceptions"):
        assert all(f" {flag} " in line for line in compiles), flag
    (link,) = [line for line in commands(root) if " -c " not in line]
    assert "-o stockfish" in link and "-lpthread" in link and link.count(".o") == 5
    assert leftovers(root) == [] and (root / "stockfish" / "src" / "stockfish").is_file()


def test_linux_binary_that_does_not_run_here_is_reported_and_removed(tmp_path: Path) -> None:
    """The binary exits when started, as one built for AVX2 does on a CPU without it."""
    root = tmp_path / "dies"
    status, lines = build(root, STUB_AVX2_DIES="1", **linux_tree(root, AVX2_CPU, marker=True))
    assert status == 1, lines
    assert lines[-1].startswith(NOT_BUILT + "the bot's engine code could not use the binary: 0 of 2 engines ready")
    assert "exited" in lines[-1] and "REQUIRE_STOCKFISH" in lines[-2]
    assert len([line for line in lines if "g++, ARCH=" in line]) == 1  # built once, not again
    assert leftovers(root) == [] and not (root / "stockfish" / "src" / "stockfish").exists()


def test_linux_build_that_does_not_compile_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "broken"
    status, lines = build(root, STUB_GXX_FAILS="1", **linux_tree(root, AVX2_CPU))
    assert status == 0, lines
    assert lines[-1].startswith(NOT_BUILT + "g++ compiled 0 of 5 files")
    assert len([line for line in lines if "g++, ARCH=" in line]) == 1
    assert leftovers(root) == [] and not (root / "stockfish" / "src" / "stockfish").exists()


def test_linux_build_says_so_when_it_cannot_read_the_cpu(tmp_path: Path) -> None:
    root = tmp_path / "unknown"
    status, lines = build(root, **linux_tree(root, NO_FLAGS))
    assert status == 0 and lines[-1].startswith(BUILT + "ARCH=x86-64-avx2")
    assert any("instruction sets are not known" in line for line in lines)
    assert not any("it has: none" in line for line in lines)


def test_required_stockfish_means_both_engines_and_a_failed_check_is_repeated(tmp_path: Path) -> None:
    """One of the two engines stays silent the first time the check starts them. With the
    marker that is a failure, and the check is run once more before the binary is given
    up; the second time both answer. (Without the marker one engine is enough.)"""
    root = tmp_path / "strict"
    env = linux_tree(root, AVX2_CPU, marker=True)
    status, lines = build(root, **{**env, "FAKE_UCI": f"mute_one={root / 'silent'}"})
    assert status == 0, lines
    assert any("REQUIRE_STOCKFISH is present" in line for line in lines[:3])
    assert any("1 of 2 engines ready in 8.0" in line and "checking once more" in line for line in lines)
    assert lines[-1].startswith(BUILT) and "2 of 2 engines ready" in lines[-1]
    assert len([line for line in lines if "g++, ARCH=" in line]) == 1  # not rebuilt for it

    root = tmp_path / "lenient"
    env = linux_tree(root, AVX2_CPU)
    status, lines = build(root, **{**env, "FAKE_UCI": f"mute_one={root / 'silent'}"})
    assert status == 0 and any("REQUIRE_STOCKFISH is absent" in line for line in lines[:3])
    assert lines[-1].startswith(BUILT) and "1 of 2 engines ready in 8.0" in lines[-1]


# ---------------------------------------------------------------------------------------
# The position-set helper, which is built before Stockfish.

def with_helper(root: Path, source: str | None = None, *, marker: bool = False) -> Path:
    """Put the helper's source (or a stand-in for it) into a tree made by tree()."""
    (root / "positions.cpp").write_text(POSITIONS_SOURCE.read_text() if source is None else source)
    if marker:
        (root / "REQUIRE_POSITIONS").touch()
    return root


def test_the_helper_is_built_checked_and_kept_whatever_becomes_of_stockfish(tmp_path: Path) -> None:
    needs_compiler()
    root = with_helper(tree(tmp_path))            # no Stockfish source at all
    status, lines = build(root)
    assert status == 0, lines
    (line,) = [line for line in lines if "POSITION SET" in line]
    assert line.startswith(SET_BUILT) and "selftest ok: 0 of 5 checks failed" in line
    assert lines[-1].startswith(NOT_BUILT + "no source in stockfish/src")
    helper = root / "positions"
    assert helper.is_file() and os.access(helper, os.X_OK) and leftovers(root) == []
    out = subprocess.run([str(helper), "selftest"], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and out.stdout.startswith("selftest ok")


def test_without_its_source_the_helper_is_reported_missing_and_the_upload_is_accepted(tmp_path: Path) -> None:
    status, lines = build(tree(tmp_path))
    assert status == 0
    assert SET_NOT_BUILT + "no positions.cpp here" in lines and not (tmp_path / "positions").exists()


def test_the_helpers_marker_rejects_an_upload_without_it(tmp_path: Path) -> None:
    root = tree(tmp_path / "missing")
    (root / "REQUIRE_POSITIONS").touch()
    status, lines = build(root)
    assert status == 1 and any("REQUIRE_POSITIONS is present: this build fails unless" in line for line in lines[:3])
    assert lines[-2] == "build: REQUIRE_POSITIONS is present, so this build fails and the upload is rejected"
    assert lines[-1].startswith(NOT_BUILT)

    needs_compiler()
    root = with_helper(tree(tmp_path / "built"), marker=True)   # the helper is there; Stockfish is not asked for
    status, lines = build(root)
    assert status == 0, lines
    assert not any("so this build fails" in line for line in lines) and (root / "positions").is_file()

    root = with_helper(tree(tmp_path / "both", marker=True), marker=True)  # both asked for, Stockfish missing
    status, lines = build(root)
    assert status == 1 and "REQUIRE_STOCKFISH" in lines[-2] and not any("REQUIRE_POSITIONS is present, so" in line for line in lines)


def test_a_helper_that_does_not_compile_or_came_with_the_upload_is_not_kept(tmp_path: Path) -> None:
    needs_compiler()
    root = with_helper(tree(tmp_path / "broken"), BROKEN_SOURCE)
    stale = root / "positions"
    stale.write_text("#!/bin/sh\necho selftest ok: built somewhere else\n")
    stale.chmod(0o755)
    status, lines = build(root)
    assert status == 0
    (line,) = [line for line in lines if "POSITION SET" in line]
    assert line.startswith(SET_NOT_BUILT) and "did not compile it" in line
    assert not stale.exists() and leftovers(root) == []

    root = with_helper(tree(tmp_path / "wrong"), "#include <cstdio>\nint main() { puts(\"selftest FAILED: 1 of 5 checks failed\"); return 1; }\n")
    status, lines = build(root)
    (line,) = [line for line in lines if "POSITION SET" in line]
    assert status == 0 and line.startswith(SET_NOT_BUILT + "its self-test did not pass: selftest FAILED")
    assert not (root / "positions").exists()

    root = tree(tmp_path / "no source")           # a binary and no source: it goes all the same
    stale = root / "positions"
    stale.write_text("#!/bin/sh\necho selftest ok\n")
    stale.chmod(0o755)
    status, lines = build(root)
    assert status == 0 and not stale.exists()


def test_linux_build_compiles_the_helper_first_and_then_stockfish(tmp_path: Path) -> None:
    root = tmp_path / "both"
    env = linux_tree(root, AVX2_CPU, marker=True)
    with_helper(root, "// stand-in\n", marker=True)
    status, lines = build(root, **env)
    assert status == 0, lines
    assert any(line.startswith(SET_BUILT + "g++, ") and "selftest ok: stand-in" in line for line in lines)
    assert lines[-1].startswith(BUILT + "ARCH=x86-64-avx2, ")
    first = commands(root)[0]
    assert first == "g++ -O2 -std=c++17 -o positions positions.cpp"   # before any Stockfish file
    assert len([line for line in commands(root) if " -c " in line]) == 5
    assert (root / "positions").is_file() and leftovers(root) == []

    root = tmp_path / "self-test fails"
    env = linux_tree(root, AVX2_CPU)
    with_helper(root, "// stand-in\n", marker=True)
    status, lines = build(root, **{**env, "STUB_SELFTEST": "FAILED"})
    assert status == 1 and not (root / "positions").exists()
    assert any(line.startswith(SET_NOT_BUILT + "its self-test did not pass: selftest FAILED") for line in lines)
    assert lines[-1].startswith(BUILT) and "REQUIRE_POSITIONS is present, so" in lines[-2]   # Stockfish is built all the same
