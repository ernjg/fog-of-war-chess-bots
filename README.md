# Fog of War chess bots (MIT 6.7980)

Bots and local tooling for the Fog of War chess challenge. The official
starter kit lives in `starter/` and is never modified; `starter/README.md` is the source of truth for the protocol, rules and limits.

## Repo tour

```
starter/          official kit (referee.py = rules + local runner; do not edit)
fow/              shared library
  protocol.py     stdin/stdout loop driving an Agent (reset / observe / act)
  local.py        helpers for running bots locally, incl. SIGSTOP/SIGCONT pausing
bots/<name>/      one folder per bot: bot.py + run.sh
tools/tournament.py   local round-robin with W/D/L table and Elo (K=8)
tools/package.py      build the upload ZIP and smoke-test it
tests/            pytest
data/             replays from tournaments (gitignored)
dist/             packaged bots (gitignored)
```

## Setup

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.14 and the
pinned `python-chess` version from `starter/requirements.txt`.

```sh
uv sync
uv run pytest
```

## Write a bot

Copy `bots/greedy/` to `bots/<name>/`, then implement an `Agent` in `bot.py`:

```python
class MyAgent(Agent):
    def reset(self, color, base, inc): ...   # color: True = White
    def observe(self, obs): ...              # 64 chars, a1..h8, before every ply
    def act(self, remaining_time): ...       # return a UCI string
```

`fow.protocol.run(agent)` owns stdout. Use `fow.protocol.log(...)` (or any
`print`, which is redirected) for diagnostics; they go to stderr. Reuse the
starter's `ObservationTracker` / `candidates` from `uniform_random.py` for
legal-move generation instead of reimplementing the rules.

`run.sh` runs `${PYTHON:-python3} -u bot.py`. The arena uses `python3`; the
local tools set `PYTHON` to the project interpreter.

## Running a tournament

```sh
uv run tools/tournament.py random greedy --games 20
```

Plays every pairing `--games` times with alternating colors at 180+2 (change
with `--base/--inc`), saves replays under `data/<timestamp>/`, and prints a
win/draw/loss table with Elo (start 1500, K=8). Like the arena, the waiting
bot's process group is paused with SIGSTOP while the other side thinks
(`--no-pause` disables this).

Single game with the stock referee:

```sh
PYTHON=.venv/bin/python uv run starter/referee.py --trusted-local \
  --white 'bash bots/greedy/run.sh' --black 'bash bots/random/run.sh' \
  --output data/one.json
```

## Package and submit (not tested yet)

```sh
uv run tools/package.py greedy
```

This copies `bots/greedy/`, `fow/` and the starter files the bot imports into
the flat folder `dist/greedy/`, zips it to `dist/greedy.zip` with `run.sh` at
the root, then unzips it to a temp dir and plays one referee game from there
against the starter baseline. 

## Caution

- Any stdout line other than `ready` / `move <uci>` forfeits the game.
- Reply `ready` within 15 s of the headers; the arena is Python 3.14 with
  python-chess 1.999 and no network.
- The arena pauses your process on the opponent's turn; you cannot compute
  then. Time paused is not charged.
