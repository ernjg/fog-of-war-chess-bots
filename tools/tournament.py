#!/usr/bin/env python3
"""Local round-robin tournament between bots in bots/.

Example: uv run tools/tournament.py random greedy --games 20

``--parallel N`` plays N games at once, each in its own worker process with its own pair
of bots (and its own SIGSTOP pausing). A game's two bots never run at the same time, so
one game needs the cores of one bot; this machine's core count divided by three is a
safe N for the Stockfish bots. Results are printed and rated in game order.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import multiprocessing
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


def _worker_init(pause: bool) -> None:
    local.use_project_python()
    if pause:
        local.install_pausing()


def play_game(spec: tuple) -> tuple:
    """One game, in whatever process this runs in. Returns what the table needs."""
    game, white, black, white_argv, black_argv, base, inc, max_plies, out_dir, pause = spec
    control = local.pause_control_factory if pause else None
    started = time.monotonic()
    replay = referee.run_match(white_argv, black_argv, base, inc, white_name=white,
                               black_name=black, max_plies=max_plies, turn_control_factory=control)
    path = Path(out_dir) / f"{game:03d}_{white}_vs_{black}.json"
    path.write_text(json.dumps(replay, indent=1) + "\n")
    return (game, white, black, replay["result"], replay["reason"], len(replay["frames"]) - 1,
            time.monotonic() - started)


def bot_name(spec: str) -> str:
    """A bot given as a run.sh path is named after its folder, not the file."""
    if "/" not in spec:
        return spec
    path = Path(spec).resolve()
    return path.parent.name if path.name == "run.sh" else path.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bots", nargs="+", help="bot names in bots/ (or run.sh paths)")
    parser.add_argument("--games", type=int, default=2, help="games per pairing, colors alternate")
    parser.add_argument("--base", type=float, default=180)
    parser.add_argument("--inc", type=float, default=2)
    parser.add_argument("--max-plies", type=int, default=1000)
    parser.add_argument("--no-pause", action="store_true", help="do not SIGSTOP the waiting bot")
    parser.add_argument("--parallel", type=int, default=1, help="games played at once (default 1)")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    if len(args.bots) < 2:
        parser.error("need at least two bots")

    pause = not args.no_pause
    _worker_init(pause)

    names = [bot_name(b) for b in args.bots]
    if len(set(names)) != len(names):
        parser.error(f"bot names must be distinct, got {names}; use paths with distinct parent folders")
    argvs = {name: local.bot_argv(spec) for name, spec in zip(names, args.bots)}
    out_dir = args.data / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = {n: {"W": 0, "D": 0, "L": 0, "elo": float(START_ELO)} for n in names}
    specs = []
    for a, b in itertools.combinations(names, 2):
        for i in range(args.games):
            white, black = (a, b) if i % 2 == 0 else (b, a)
            specs.append((len(specs) + 1, white, black, argvs[white], argvs[black], args.base,
                          args.inc, args.max_plies, str(out_dir), pause))

    def rate(outcome: tuple) -> None:
        game, white, black, result, reason, plies, seconds = outcome
        print(f"#{game:3d} {white} (W) vs {black} (B): {result:7s} {reason}"
              f"  [{plies} plies, {seconds:.1f}s]", flush=True)
        if result == "*":
            print("     not rated (infrastructure failure)", flush=True)
            return
        score_w = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[result]
        for name, score in ((white, score_w), (black, 1 - score_w)):
            stats[name]["W" if score == 1 else "L" if score == 0 else "D"] += 1
        ew = expected(stats[white]["elo"], stats[black]["elo"])
        stats[white]["elo"] += K_FACTOR * (score_w - ew)
        stats[black]["elo"] += K_FACTOR * ((1 - score_w) - (1 - ew))

    if args.parallel <= 1:
        for spec in specs:
            rate(play_game(spec))
    else:
        done: dict[int, tuple] = {}
        next_game = 1
        context = multiprocessing.get_context("spawn")
        with concurrent.futures.ProcessPoolExecutor(args.parallel, mp_context=context,
                                                    initializer=_worker_init, initargs=(pause,)) as pool:
            for outcome in pool.map(play_game, specs):
                # map yields in order, so games print and rate in order as each completes
                rate(outcome)

    print(f"\nReplays: {out_dir}\n")
    width = max(len(n) for n in names)
    print(f"{'bot':{width}}   W   D   L     Elo")
    for name in sorted(names, key=lambda n: -stats[n]["elo"]):
        s = stats[name]
        print(f"{name:{width}} {s['W']:3d} {s['D']:3d} {s['L']:3d}  {s['elo']:6.1f}")


if __name__ == "__main__":
    main()
