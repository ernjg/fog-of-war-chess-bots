#!/usr/bin/env python3
"""Package a bot for upload: flat folder -> ZIP -> smoke-test game from the unzipped copy.

Example: uv run tools/package.py greedy
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402
import fow.local as local  # noqa: E402
import referee  # noqa: E402

STARTER_FILES = ["referee.py", "uniform_random.py"]  # what fow/ and the bots import
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".DS_Store")


def stage(bot_dir: Path, staging: Path) -> None:
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(bot_dir, staging, ignore=IGNORED)
    shutil.copytree(ROOT / "fow", staging / "fow", ignore=IGNORED)
    for name in STARTER_FILES:
        shutil.copy2(fow.STARTER_DIR / name, staging / name)
    links = [p for p in staging.rglob("*") if p.is_symlink()]
    if links:
        raise SystemExit(f"Symlinks are not accepted by the arena: {links}")
    if not (staging / "run.sh").is_file():
        raise SystemExit("run.sh must be at the ZIP root")


def zip_folder(staging: Path, zip_path: Path) -> int:
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(staging))
                count += 1
    return count


def smoke_test(zip_path: Path, name: str, base: float, inc: float, max_plies: int) -> bool:
    local.use_project_python()
    with tempfile.TemporaryDirectory(prefix="fow-smoke-") as tmp:
        unzipped = Path(tmp) / "bot"
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(unzipped)
        packaged = ["bash", str(unzipped / "run.sh")]
        baseline = [sys.executable, "-u", str(fow.STARTER_DIR / "baseline.py"), "--seed", "1"]
        print(f"Smoke test: {name} (W, from {unzipped}) vs starter baseline (B) at {base:g}+{inc:g}")
        replay = referee.run_match(packaged, baseline, base, inc, white_name=name,
                                   black_name="baseline", max_plies=max_plies)
    plies = len(replay["frames"]) - 1
    print(f"  {replay['result']}: {replay['reason']} ({plies} plies)")
    if replay.get("failedSide") == "white" or replay["result"] == "*":
        print("  FAILED: the packaged bot did not complete the game cleanly")
        for report in replay.get("studentReports", []):
            print("  ", report)
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bot", help="bot name in bots/")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--base", type=float, default=60)
    parser.add_argument("--inc", type=float, default=1)
    parser.add_argument("--max-plies", type=int, default=1000)
    parser.add_argument("--no-smoke", action="store_true")
    args = parser.parse_args()

    bot_dir = local.BOTS_DIR / args.bot
    if not bot_dir.is_dir():
        raise SystemExit(f"No such bot: {bot_dir}")
    staging = args.out / args.bot
    zip_path = args.out / f"{args.bot}.zip"
    args.out.mkdir(parents=True, exist_ok=True)

    stage(bot_dir, staging)
    count = zip_folder(staging, zip_path)
    print(f"Wrote {zip_path} ({count} files, {zip_path.stat().st_size / 1024:.1f} KiB)")
    print("Contents:", ", ".join(sorted(str(p.relative_to(staging)) for p in staging.rglob("*") if p.is_file())))

    if args.no_smoke:
        return
    if not smoke_test(zip_path, args.bot, args.base, args.inc, args.max_plies):
        sys.exit(1)
    print(f"OK: upload {zip_path} on the Submit page.")


if __name__ == "__main__":
    main()
