#!/usr/bin/env python3
"""Local round-robin tournament between bots in bots/.

Example: uv run tools/tournament.py random greedy --games 20
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow.local as local  # noqa: E402
import referee  # noqa: E402

K_FACTOR = 8
START_ELO = 1500


def expected(rating: float, other: float) -> float:
    return 1 / (1 + 10 ** ((other - rating) / 400))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bots", nargs="+", help="bot names in bots/ (or run.sh paths)")
    parser.add_argument("--games", type=int, default=2, help="games per pairing, colors alternate")
    parser.add_argument("--base", type=float, default=180)
    parser.add_argument("--inc", type=float, default=2)
    parser.add_argument("--max-plies", type=int, default=1000)
    parser.add_argument("--no-pause", action="store_true", help="do not SIGSTOP the waiting bot")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    if len(args.bots) < 2:
        parser.error("need at least two bots")

    local.use_project_python()
    control = None
    if not args.no_pause:
        local.install_pausing()
        control = local.pause_control_factory

    names = [Path(b).name if "/" in b else b for b in args.bots]
    argvs = {name: local.bot_argv(spec) for name, spec in zip(names, args.bots)}
    out_dir = args.data / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = {n: {"W": 0, "D": 0, "L": 0, "elo": float(START_ELO)} for n in names}
    game = 0
    for a, b in itertools.combinations(names, 2):
        for i in range(args.games):
            white, black = (a, b) if i % 2 == 0 else (b, a)
            game += 1
            started = time.monotonic()
            replay = referee.run_match(argvs[white], argvs[black], args.base, args.inc,
                                       white_name=white, black_name=black,
                                       max_plies=args.max_plies, turn_control_factory=control)
            plies = len(replay["frames"]) - 1
            path = out_dir / f"{game:03d}_{white}_vs_{black}.json"
            path.write_text(json.dumps(replay, indent=1) + "\n")
            result = replay["result"]
            print(f"#{game:3d} {white} (W) vs {black} (B): {result:7s} {replay['reason']}"
                  f"  [{plies} plies, {time.monotonic() - started:.1f}s]", flush=True)
            if result == "*":
                print("     not rated (infrastructure failure)", flush=True)
                continue
            score_w = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[result]
            for name, score in ((white, score_w), (black, 1 - score_w)):
                stats[name]["W" if score == 1 else "L" if score == 0 else "D"] += 1
            ew = expected(stats[white]["elo"], stats[black]["elo"])
            stats[white]["elo"] += K_FACTOR * (score_w - ew)
            stats[black]["elo"] += K_FACTOR * ((1 - score_w) - (1 - ew))

    print(f"\nReplays: {out_dir}\n")
    width = max(len(n) for n in names)
    print(f"{'bot':{width}}   W   D   L     Elo")
    for name in sorted(names, key=lambda n: -stats[n]["elo"]):
        s = stats[name]
        print(f"{name:{width}} {s['W']:3d} {s['D']:3d} {s['L']:3d}  {s['elo']:6.1f}")


if __name__ == "__main__":
    main()
