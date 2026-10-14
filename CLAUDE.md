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
