# Local experiment: weighted roots in two-ply PCFR+

This experiment was implemented and tested in a separate local working tree on
2026-11-16. It was never uploaded to the arena. This report records that trial;
it does not add the experimental implementation to this branch or change v4.

## Question and approach

Does giving plausible hidden boards more influence improve the Stockfish-leaf
PCFR+ hybrid, and does the weighted hybrid outperform frozen `obscuro_v4`?

The local candidate `obscuro_pcfr_weighted` retains the fixed two-ply game,
predictive CFR+ solver and depth-one Stockfish leaves of the unweighted hybrid
`obscuro_pcfr`. It enables v4's existing opponent likelihood model and carries
the resulting probabilities into the game's root chance distribution.

For each hypothetical parent board, Stockfish scores possible opponent moves
one ply deep. A softmax of those scores supplies 80% of the move probability;
the remaining 20% is uniform over Fog of War moves. A successor board inherits
its parent's weight multiplied by the move's likelihood. Observations remove
inconsistent boards.

The experiment draws up to 200 roots in proportion to the belief weights,
evaluates each distinct sampled root once, and gives the solver normalized
draw multiplicities for completed roots. It does not multiply those counts
by the original probabilities a second time. The solver therefore accounts
for uncertainty using the posterior distribution rather than equal roots.
Computing these probabilities counts against the move's clock budget.

## Match design and results

The first comparison measured weighting against the unweighted hybrid. The
selected weighted candidate then faced frozen v4. Each comparison used
**120 local games at 36+0.4**, 60 per listing order with alternating colors,
four concurrent games and process-group pausing of the waiting bot. Parameters
stayed fixed. The weighted search implementation was unchanged between the
control comparison and the v4 challenge.

All W-D-L counts below are from the weighted candidate's side. Score is
`(wins + 0.5 * draws) / games`.

| Opponent | Candidate listed first | Candidate listed second | Total W-D-L | Score |
| --- | --- | --- | --- | --- |
| Unweighted Stockfish-leaf PCFR+ | 39-0-21 | 38-0-22 | **77-0-43** | **64.2%** |
| Frozen v4 | 20-1-39 | 19-1-40 | **39-2-79** | **33.3%** |

The strict win rate against v4 was 32.5%. All 240 games finished without
forfeits or protocol warnings. Retained logs show the intended search in every
candidate game and no engine/helper failures or tracebacks. The candidate used
its intended material-evaluation fallback twice in the control comparison and
once against v4. Some diagnostics retain only their final 16 KiB; replay frames
and game results are complete.

## Interpretation and decision

Weighting improved the hybrid against its unweighted control in both listing
orders. This is evidence for using probabilities in the sampled PCFR+ game;
it is not evidence that the weighted hybrid is stronger than v4. The direct
v4 challenge lost in both orders and failed the planned 50% screen for a
full-clock comparison. No 180+2 strength match or arena activation followed
for this candidate.

The earlier unweighted hybrid scored 20.4% against v4 in a separate match.
That number and this 33.3% are historical comparisons, not a paired estimate
of the effect of weighting. The direct 77-0-43 control comparison is the test
that isolates the weighting change within the hybrid.

## Evidence

The [compact result record](weighted-pcfr-results.json) includes both listing
orders and colors, replay-manifest digests and source provenance. The control
comparison used local commit `8eddc5f75b069e039678ab7b8bd2b4e1cb3af7fb`; the v4
challenge used `f135eb2054b0cd4ec2d681f208113dc0232aa80d`. Those local commits
are recorded for provenance and are not included by this documentation change.
The local settings were `--search pcfr --pcfr-weighted --leaf-depth 1`.

Original local artifacts are under `data/pcfr-ablations/phase1/` and
`data/pcfr-ablations/v4-challenge/`. Only the weighting comparisons are reported
here. Raw replays and experimental source are not bundled, so the compact
record supports checking totals but is not a runnable reproduction.
