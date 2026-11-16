# Project notes for Claude

- `starter/` is the official kit. Never modify it. `starter/README.md` is the
  source of truth for the protocol, rules and limits; `starter/referee.py`
  implements the rules. Reuse it (and `ObservationTracker` from
  `starter/uniform_random.py`); do not reimplement rules.
- **Stdout is reserved for the protocol.** A bot may only ever write `ready`
  and `move <uci>` to stdout; anything else forfeits the game. All logging
  goes to stderr via `fow.protocol.log`. `fow.protocol.run` redirects
  `sys.stdout` to stderr for this reason.
- **Never commit or log the team token or team link.** Keep them out of
  source, the ZIP, replays, stderr and this repo (`.env` is gitignored).
- Runtime on the arena: Python 3.14, python-chess 1.999, no network, no
  pip. Dependencies must be inside the ZIP.
- The arena pauses the bot process on the opponent's turn; the local
  tournament mimics this with SIGSTOP/SIGCONT.
- Workflow: `uv sync`, `uv run pytest`, `uv run tools/tournament.py a b --games N`,
  `uv run tools/package.py <bot>`.
- **The working bot is `bots/obscuro` with `fow/obscuro`.** All new work, the next
  version included, happens there.
- **Every folder named `bots/<name>_v<N>` is frozen.** `bots/obscuro_v<N>` is the bot
  that was uploaded as arena version N, with its own copy of the search code in
  `bots/obscuro_v<N>/obscuro_v<N>/`. Never edit a frozen bot, not even to fix a bug, and
  never regenerate `tests/frozen_bots.sha256` to make a test pass. A search or rename
  across the repo also matches the frozen copies. Leave those matches alone. To try an
  idea on an old version, copy its folder to a new name without a version number.
- Frozen bots still import `fow/__init__.py` and `fow/protocol.py`, and their protocol
  test rows use `tests/fake_uci_engine.py`. Keep all three working for every frozen bot.
- Do not create a numbered folder before a version is uploaded. Commit before
  uploading and package from that commit. When an upload differs significantly from
  the last frozen version (a different search or a different way of tracking
  positions, not a fix or tuning), freeze it with the steps in `docs/versions.md`.
- Compare versions by playing them, for example
  `uv run tools/tournament.py obscuro obscuro_v4 --games 60 --base 36 --inc 0.4`. Each
  version that uses Stockfish needs its own build first. One short match proves nothing:
  identical bots have finished 30 games anywhere from 23% to 60%. Play both listing
  orders, at least 60 games each way, before concluding that one version is stronger.
  `docs/versions.md` has the steps.
