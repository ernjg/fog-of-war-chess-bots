# Local experiment: Stockfish leaves in two-ply PCFR+

This experiment was implemented and tested in a separate local working tree on
2026-11-16. It was never uploaded to the arena. This report records that trial;
it does not add the experimental implementation to this branch or change v4.

## Question and approach

Does a stronger leaf evaluator improve the existing shallow PCFR+ search, and
does that hybrid outperform frozen `obscuro_v4`?

The candidate, locally named `obscuro_pcfr`, builds a fixed two-ply Fog of War
game: our move followed by an opponent reply. Alternating predictive CFR+
(PCFR+) solves the sampled game, and the most probable action in its final
strategy is played. Stockfish 19 evaluates nonterminal leaves at depth one,
replacing the material-and-visibility heuristic. King-capture outcomes retain
their terminal values.

Roots are equally likely. The opponent likelihood model is disabled before
belief sampling, so weighted sampling cannot enter the supposedly unweighted
control. The C++ belief helper, clock accounting, repetition rule, two-ply
structure and solver are shared with the material-only comparison setting.
The candidate has up to 200 roots and two Stockfish processes. It is a shallow
hybrid, not the paper's complete growing-tree and safe-resolving pipeline.

This differs from v4's normal search, which evaluates moves with separate,
deeper Stockfish searches on sampled boards and combines their values. V4's
material PCFR+ search is ordinarily only a fallback.

## Match design and results

Each comparison used 120 local games: 60 in each listing order, alternating
colors within an order, at **36 seconds plus 0.4 seconds per move**. Four games
ran concurrently on an Apple M1 Pro with eight cores and 16 GiB RAM. The waiting
bot's process group was paused. Parameters stayed fixed during the matches.
The material control was the working comparison setting `obscuro_material`,
not the historical frozen v2 with its older clock behavior.

All W-D-L counts below are from the candidate's side. Score is
`(wins + 0.5 * draws) / games`.

| Opponent | Candidate listed first | Candidate listed second | Total W-D-L | Score |
| --- | --- | --- | --- | --- |
| Material-only PCFR+ | 57-0-3 | 56-0-4 | **113-0-7** | **94.2%** |
| Frozen v4 | 12-0-48 | 12-1-47 | **24-1-95** | **20.4%** |

The strict win rate against v4 was 20.0%. All 240 games finished without
forfeits or protocol warnings. The retained logs show the intended
Stockfish-leaf search in every candidate game and no engine/helper failures or
tracebacks. Some diagnostics retain only their final 16 KiB; the game results
and replay frames are complete.

## Interpretation and decision

Stockfish leaves substantially improved this fixed shallow solver over its
material-only control. The resulting hybrid nevertheless lost heavily to v4
in both listing orders. That comparison does not isolate search depth from
belief weighting: v4 differs in both respects.

The result supports keeping the tested hybrid experimental. It does not
establish its strength at the arena's 180+2 clock or against the arena field.
No candidate was activated and no numbered arena version was created.

## Evidence

The [compact result record](stockfish-leaf-pcfr-results.json) includes both
listing orders and colors, replay-manifest digests and source provenance.
The local implementation commit was
`79dcc52fa573756de157432dab36418488a77f2a`; it is recorded for provenance and
is not included by this documentation change. Its local selection was
`--search pcfr` (equal roots and depth-one Stockfish leaves).

Original local artifacts are under `data/hybrid-validation/`. Raw replays and
the experimental source are not bundled with this report, so the compact
record supports checking the reported totals but is not a runnable reproduction.
