# eBotI: the variants tried against v4, and why each one failed

Notes on the experimental bot `bots/eBotI`, 2026-11-17. Every variant below was built in
eBotI and played against the frozen `bots/obscuro_v4`. The variants are not separate bots:
eBotI selects them with environment variables (`FOW_SEARCH`, `FOW_ROOTS`, `FOW_CVAR`,
`FOW_RISK_UNIFORM`, `FOW_TIME`, `FOW_HAZARD`, `FOW_ENGINES`), and its defaults are now the v4
search settings plus the king hazard of section 8. "v4" means the arena bot: full consistent position set (cap 200k)
weighted by a Stockfish 1-ply opponent model, 64 sampled boards scored by Stockfish per move,
value `-risk + (1-risk)*mean`, king-attacked boards weighted x6.

Two facts frame all of it:

- **What a loss looks like.** In 150 arena games (83-4-63) every one of the 63 losses ended
  with our king attacked by a piece we could not see. Among the 26 losses to lower-rated
  bots, a safe move existed in 24; in 15 the king itself stepped onto the attacked square;
  in 8 it already stood in an unseen check and did not move. The attacker was a rook or
  queen 20 times: a long line we could not look down.
- **What we can measure.** A 60-game match has a standard error of 6.4 points. Identical
  bots have finished 30 games anywhere from 23% to 60%. Any change worth less than about
  10 points cannot be seen locally in a day. Only structural changes are testable this way.

## 1. Obscuro's search (KLUSS + one-sided GT-CFR), in Python, then in C++

**What.** The paper's pipeline: subgame roots sampled from the belief (KLUSS, MinInfosetSize
256), one-sided growing tree with PUCT exploration, PCFR+ with last-iterate play, resolve and
maxmargin gadgets with alt values `u - gift`, purification, Stockfish at the leaves (depth 1
at leaves, depth 4 or 8 under the roots). The C++ version reached 370-750k nodes and
7-10 plies per move at 180+2, about half the paper's 1.07M nodes.

**Result.** Lost to v4's search in every configuration: 0-10, 1-9, 3-7 in short matches.
In the lost games the tree's own evaluation was below -0.85 by move 15.

**Why, in theory.**

- *The value of equilibrium play is bounded by how much the opponent exploits you; the
  value of depth is not.* A game-theoretic search buys robustness against an opponent who
  models our strategy and best-responds to it. The arena pool is engine-driven bots that
  do not model us at all, so the exploitability we removed was never being cashed in. What
  decides these games is tactics on the hidden part of the board, which is a question of
  evaluation accuracy, and evaluation accuracy is what we gave up: depth-1 Stockfish at a
  million leaves against v4's depth 8-12 on 64 boards. The leaf evaluator bounds the whole
  tree; a sound solver over a blind evaluator is a blind solver.
- *The node budget is spent on strategy, not on evaluation.* Each node of a GT-CFR tree
  holds a regret and strategy table for a whole infoset; the iterations needed for PCFR+ to
  approach equilibrium at depth 2 and beyond (hundreds) are not available when the tree
  also has to grow. With ~10 passes per node the strategies deeper than the root are far
  from equilibrium, and the values propagated up through them are noise with a bias toward
  whatever the exploring mix happened to try.
- *Compute.* The paper's result is at 5 s/move on a far better engineered system; the arena
  gives two physical cores. We were at half the nodes with a weaker evaluator per node.

**Natural response.** Keep v4's deep per-board evaluation and use a tree only for what depth
cannot see: the information effect of a move (what it reveals and what it hides). That is a
much smaller object than a full GT-CFR tree. Not attempted.

## 2. Breadth: 384 scored boards instead of 64

**What.** Score six times more belief boards per move at the same budget, on the theory that
losses come from boards never scored.

**Result.** At 36+0.4, 4.5-13.5 against v4 (depth fell to 1-7 plies). At 180+2 depth was
equal (10-12) and the result was 4.5-7.5 (with CVaR) and 4-6 (without).

**Why, in theory.**

- *Effective sample size.* The belief weights are concentrated: the logs show an effective
  sample size (ESS) of 1-50 boards on most moves. Sampling 384 boards from a distribution
  with ESS 36 adds almost nothing to the weighted mean; the extra boards are near-duplicates
  by weight. Breadth beyond the ESS is wasted budget.
- *The error is bias, not variance.* Averaging more boards reduces sampling variance. The
  dominant error in a move's value is the evaluator's systematic error at shallow depth
  (horizon effects, unseen tactics), which is the same on every board and does not average
  out. Trading depth for breadth trades a bias we can shrink for a variance that was already
  small.

**Natural response.** Set the board count from the measured ESS of the belief, not a constant;
spend the remainder on depth. Trivial to do, but worth less than the measurement floor.

## 3. Risk-averse aggregation (CVaR over boards)

**What.** A move's value is `0.5 * mean + 0.5 * CVaR_30%`: half the weighted mean, half the
mean of its worst 30% of boards by weight.

**Result.** B (384 boards, no CVaR) 4.5-7.5 vs v2 (with CVaR) 5-9: no help, probably harm.
Lost games show the evaluation sliding from +0.1 to -0.9 over moves 10-25: passivity.

**Why, in theory.**

- *Wrong adversary.* CVaR over boards is pessimism about nature: it assumes the board is
  chosen against us. The board is fixed; only the opponent's future moves are adversarial,
  and Stockfish already minimaxes those inside each board. Pessimism about which board we
  are on is justified only if the belief is miscalibrated in a known direction, and then the
  fix is the belief, not the aggregation.
- *The tail does not discriminate between moves.* The worst boards are the ones where the
  opponent's hidden pieces are best placed; on those boards every one of our moves scores
  badly. So the tail term adds a nearly constant penalty across moves plus noise from the
  few boards in the tail (ESS again), and shifts the choice toward moves that are merely
  less bad on hopeless boards: quiet, passive moves. In Fog of War the initiative (seeing
  more squares, forcing the opponent) is worth more than insurance against rare boards.

**Natural response.** None in this form. Risk aversion belongs in the king-loss term, which
is already a probability of catastrophe, not in the evaluation of ordinary positions.

## 4. Counting king risk half by weight, half uniformly over the set

**What.** The share of belief positions where a move loses the king, computed over the whole
set, with half the count ignoring the belief weights (because the weights give the truth
only 2x the odds of a random consistent position).

**Result.** Replay metric slightly better; games worse (the uniform half is in v2 and B,
absent in A, and A was the only configuration that held even).

**Why, in theory.**

- *The set is dominated by implausible histories.* The number of positions consistent with
  our observations grows with the number of pointless move sequences the opponent could
  have made; those are the bulk of the set and nearly all have negligible probability. Under
  a uniform measure, "a piece attacks square X" is true in roughly the same share of
  positions for every X in the fog, so uniform risk is close to a constant that depends only
  on whether the king moved into the fog, and carries almost no information about which
  move is dangerous. It penalizes every active king move alike and leaves the dangerous
  quiet moves alone.
- *The mistake it was meant to fix is real but needs a different measure.* The belief gives
  the truth a weight share of 0.02 or less at the fatal decisions. Correcting that by a
  uniform measure replaces one wrong measure with another; what is needed is the empirical
  frequency of the catastrophe (section 8).

## 5. Exact king risk and a one-ply trap check over the whole set

**What.** Compute exactly what v4 estimates from 1024 scanned boards: the weighted share of
the set where a move loses the king at once, plus the share where the opponent can then
give a check we cannot meet. In C++, 12-30 ms per move.

**Result.** A (v4 + this, nothing else) 7-6 against v4: indistinguishable.

**Why, in theory.** Estimating a weighted share from 1024 draws of a distribution with ESS
1-50 is already exact up to the tail that carries under 2% of the weight. The exact count
differs from v4's sample only where the weights are tiny, and those are the very positions
the belief is wrong about. Exactness fixes an estimation error of order 0.01 in a quantity
whose real error is the belief's miscalibration of order 1. The trap term is correct and
rare (an unanswerable check one ply out), and the forced losses it catches are mostly
already lost positions.

## 6. Opponent model boosts (checks x3, x6; captures x1.5)

**What.** Make the 1-ply opponent model prefer checks and captures, hoping to put more
weight on the attacking positions that kill us.

**Result.** Calibration on replays: the truth's weight is 2.0x uniform under the current
model and no better under any boost; at the end of lost games 2.4x. Not adopted.

**Why, in theory.**

- *The opponents are engines.* A Stockfish 1-ply model already captures how an engine-like
  opponent chooses; checks and captures are not more frequent in their play than the model
  says, so boosting them moves weight onto positions that did not happen.
- *A weak per-move likelihood cannot identify the state.* After k opponent moves the truth's
  weight relative to a typical consistent position is a product of k per-move likelihood
  ratios, each about 1.2-2 (the true move ranks in the top 20% under the model), against a
  set that grows by orders of magnitude. The posterior stays diffuse: 2x uniform on a set of
  10^4 is a share of 0.0002. No reweighting of a 1-ply model changes that order of
  magnitude. Identifying the state would need a model of *this* opponent's policy (they are
  deterministic engines; their moves in past games are public), not a generic one.

**Natural response.** Per-opponent policy models fitted on their arena replays. Their names
are in the game headers, their moves are in the replays, and they are deterministic bots.
This is the one belief improvement with a theoretical route to concentrated weights. Not
attempted; it is a large piece of work and its payoff is bounded by how many of their
positions we can evaluate.

## 7. Time: more when uncertain, and 4 engines

**What.** Budget x1.4 when the set is large; 4 Stockfish engines instead of 2.

**Result.** No measurable effect; the 4-engine setting flattered every local test.

**Why, in theory.**

- *The clock rule has almost no slack.* v4 spends `remaining/30 + 0.8*increment`, 7.6 s
  early, decaying; it ends arena games with 82 s unused on average. Simulating alternative
  rules over the observed game lengths (13-75 moves) gives at best 6.2 s average think
  against 5.2 s: +19% time, roughly +15 Elo by the usual time-to-strength slope, below
  what we can measure. The decay is also the right shape: the fatal decisions come at moves
  30-50, when any front-loaded rule has less left.
- *The arena has two physical cores.* Four engines on two cores with hyperthreading gives
  perhaps +25% throughput, not 2x. Locally, eBotI's four engines ran on four real cores while
  v4 ran on two, so every eBotI-vs-v4 match before this note overstated eBotI by a factor of
  two in compute. eBotI is now set to 2 engines.

## 8. What the data suggests instead: an empirical king hazard (current attempt)

The failures above share a cause: every attempt routed the fix through the belief weights,
and the belief is diffuse by an order of magnitude at exactly the decisions that lose. The
alternative is to measure the catastrophe directly. Over 5,858 of our arena decisions, the
probability that an unseen piece attacks our king after a move is a steep function of how
many unseen squares have an open line to the king's square (0.05% below four such squares,
16% at twenty or more) and of the opponent's material. A logistic fit on those features is
calibrated across its range. eBotI now compounds this hazard with the belief's risk:
`risk = 1 - (1 - belief_risk)(1 - hazard)`.

**Why this is different.** It is the marginal probability of the event we die from, estimated
from the arena's own frequency, independent of the weights we know are wrong. It is cheap
(a ray count per candidate move), and it attacks the 23 of 26 fatal decisions that were a
king walking onto, or staying on, an exposed square.

**Known limits.** The hazard was measured under v4's own move choices (selection bias: the
alternatives it rejected may carry different hazard); it is a marginal rate, so it will
sometimes penalize a square that happens to be safe and miss a quiet line with a queen on
it; and the opponent pool will drift. The replay test on the 63 lost games (fatal decision
plus three ordinary ones per game, search with and without the hazard on the same belief,
judged on the true board) is the first check; a long match against v4 at 180+2 with 2
engines is the second.

## Measurement notes

- *The per-move replay metric does not predict games.* Mean true-board value lost per
  decision favored v2 by 11% while v2 lost 5-9. Fog-of-war games are decided by rare
  catastrophic events (one unseen attack ends the game), a heavy-tailed loss; a mean over
  decisions at depth 8 is dominated by small positional differences and blind to the tail.
  Any metric for this game must count catastrophes, not average evaluations.
- *The clean local judge is a long match at 180+2 with 2 engines per bot.* 300 games bring
  the standard error to about 3 points; that is an overnight run at four games in parallel.
