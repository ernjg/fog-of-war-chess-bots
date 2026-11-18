# Arena measurement scripts

Scripts that judge a bot on arena data instead of self-play. All read the public arena API
(`https://6s890.lids.mit.edu/api/...`, no token) and cache replays under `data/arena/`
(override with `ARENA_CACHE`). Run from the repo root with `uv run python tools/arena/<script>`.

| script | what it answers |
| --- | --- |
| `opponents.py <team id> <games>` | our record per opponent against the Elo prediction |
| `clocks.py <team id> <games>` | how much clock we leave unused, think time per move |
| `loss_patterns.py <team id> <games> [max rating]` | how our losses end (replays go into the cache) |
| `hazard.py <team id> <games>` | rate of unseen attacks on our king by exposure of the king's square |
| `belief_calibration.py <first> <last>` | replays the belief: predicted vs realized checks and threats |
| `paired_aggregation.py <first> <last> <budget>` | one Stockfish pass per decision, saved so scoring rules can be compared offline |
| `rules_offline.py` | scores aggregation rules on the saved evidence, judged on the true board |
| `gauntlet_metrics.py label=data/<run> ...` | per configuration: score and fog events (material lost to unseen attackers, king moves) over local games |

Findings from these are in `APPROACHES.md` and `docs/arena-opponents.md`.

Added 2026-11-18 (the cache holds `replays_cache.pkl` and `games_list.json` from `loss_patterns.py`):

| script | what it answers |
| --- | --- |
| `truth_in_set.py <first> <last> [losses\|all]` | replays our games through eBotI's position set: is the true board in the set, with what weight share, at every decision |
| `truth_risk.py <first> <last> [losses\|all]` | the same plus the exact king risk of every candidate move, to compare the chosen move with the safest one |
| `opp_model_calib.py <first> <last>` | log-likelihood of the opponents' real moves under the true-board one-ply model and under a blind (opponent's view) model |
| `match_anatomy.py <data dir>` | per bot in a local tournament: score, how its losses end (walk-in / unanswered unseen check / seen), king moves, material lost to unseen attackers |
