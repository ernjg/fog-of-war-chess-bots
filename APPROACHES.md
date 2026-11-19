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

## 8. An empirical king hazard (tested, not adopted)

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

**Why it failed, in theory (independent review).** The rate was fitted on the moves v4
chose, i.e. on moves the belief had already passed as safe, so it is a residual over the
belief; evaluated on the moves v4 rejected it under-predicts by 4-10x. Compounding it with
the belief's own risk double counts wherever the belief is informed. Its spread between
moves exceeds 0.05 in only 14% of decisions, almost all positions already lost (the
opponent led by 8 points of material on average at the fatal decisions). The self-play match
against v4 stood 42-42 after 84 games and could not have shown a 3-point effect in fewer
than about 2,200 games. Off by default (`FOW_HAZARD=0`).

## 9. Recalibrating the belief's weights (tested, no effect)

**What.** Replaying all 150 arena games through the belief (4,807 decisions) to compare what
the belief predicts with what happened. Checks from the fog: predicted 1.7%, realized 1.6%,
calibrated; with the x6 attacked-king weight the search acts as if the share were 2-2.5x the
real one in the decisions that matter, and moves the king in 56-63% of them. Threats to the
piece we just moved: under-predicted (5% predicted where 11% happened); a weight of 1.5 per
threatened piece calibrates every bucket. Both are now `FOW_ATTACKED` and `FOW_THREAT`.

**Result.** On identical Stockfish evidence (1,393 decisions, 40 games) changing the
attacked weight from 6 to 1 changes 18 decisions and leaves king moves at 237 vs 235; the
threat weight changes 73 and nothing improves.

**Why.** The x6 weight only matters where the raw belief already puts tens of percent on
being in check, and there moving the king is right under any weight. The king walks are the
rational choice under a belief that is calibrated on average and wrong only in the tail,
where the true attacker sits on a board of negligible weight. No reweighting of the boards
we have can repair a tail the weights cannot see.

## 10. Worst-board mix and king discipline (offline gain, no gain in games)

**What.** StrangeFish2's rule, value = 0.7 x weighted mean + 0.3 x unweighted worst scored
board (`FOW_WORST`), and a penalty on king moves while the belief says we are not in check and
we have 5+ pieces (`FOW_KING_PENALTY`). Both scored offline on the saved evidence of 1,393
decisions, then played against the frozen v3 (arena 45%) for 80 games each at 180+2.

**Result.** Offline the mix lowered true-board value lost from 0.0657 to 0.0633 and moves
into fog attacks from 310 to 273; the king penalty cut king moves from 242 to 96 and next-ply
king losses from 19 to 15 at a cost in true-board value. In games: v4 0.825, mix 0.825,
mix + penalty 0.812, with 14, 14 and 14 losses, and no reduction in material lost to unseen
attackers (8.1, 9.4, 10.0 per game). Both off by default.

**Why.** The next-ply metrics measure the move; the games are lost two to five plies later,
when the slider swings onto the line the king or piece has walked onto. A rule that makes
the next move safer without changing where the pieces stand two moves later does not change
the outcome, and a king that moves less stands longer on the line it is already on.

## 11. Benchmarks (what finally measures anything)

- Self-play against v4 measures only the differential of two near-identical bots: 42-42
  after 84 games, and about 2,200 games for a 3-point effect.
- A cheap sparring bot (`bots/sparring`: Stockfish on a last-seen board, 30 ms a move, four
  styles) is beaten 90-0 by v4 and separates nothing. The arena's winners are engine-on-
  belief bots of our own class (34% top-1 agreement with true-board Stockfish, same as us,
  4-5 s a move), not heuristics (`docs/arena-opponents.md`).
- The frozen v3 is an arena-class, genuinely different opponent; v4 scores 0.825 against it.
  80 games there have a standard error of 4 points, so only large effects show.
- Same-evidence offline scoring (`tools/arena/paired_aggregation.py`, then
  `rules_offline.py`) compares aggregation rules with no engine noise, in seconds, but judges
  only the next ply.
- *The per-move replay metric does not predict games.* Mean true-board value lost per
  decision favored v2 by 11% while v2 lost 5-9. Fog-of-war games are decided by rare
  catastrophic events, a heavy-tailed loss; a mean over decisions is blind to the tail.
- The arena itself is the only judge with enough games for a 3-point change.

## 12. What the belief knew at the fatal decisions (measured 2026-11-18)

**What.** Every lost arena game replayed through our own position set (same helper as v4,
cap 200k, opponent model on), asking at each of our decisions whether the true board is in
the set, its weight share, and the exact king risk of every candidate move
(`tools/arena/truth_in_set.py`, `truth_risk.py`).

**Result.** The true board is in the set at 92% of decisions (100% to ply 20; 14 of 55 games
lose it once, always when the set hits the 200k cap) and at 87% of the 40 fatal king walks.
There the belief was not blind: the chosen move lost the king at once in a median 12% of
the set's weight (quartiles 5% and 19%), the safest alternative in 0.1%; the chosen move was
the least risky one in 15% of cases. Across all decisions the risk is calibrated, even
conservative: moves given 3-10% died 15% of the time, moves given over 10% died 22%. In won
games the bot takes such risks 0.9 times a game, in lost games 3.4 times.

**Why.** The value is ``-risk + (1 - risk) * mean``: a death and a lost position cost the
same. The mean is Stockfish's, which scores a board as if both sides saw everything from
there on, so a rook down reads as hopeless (-0.9) and a 12% chance of instant death is cheap
beside a move that lifts the mean by 0.3. In the fog a rook down is not hopeless: the
opponent has to find the king. The exchange rate between death and evaluation is wrong by
several times. Greek Gift's king steps onto an attacked square in 1.1% of its king moves
(ours 6.1%) and it keeps that rate in won positions.

## 13. Pricing the king (``FOW_RISK_LAMBDA``; tested, no gain)

**What.** ``-lambda * risk + (1 - risk) * mean`` with lambda 5, exact risk over the whole set.

**Result.** 21-5-29 against v4 at 60+1 (54 games). In eBotI's 28 losses the logged value
was below -0.5 six moves before the end in 24; in v4's 20 losses, in 16. The fatal risks
were taken in positions already lost: by then every king move was risky (the logged risk of
the fatal move was 0.1-1.0) and pricing the risk changes nothing.

**Why.** The walk-in is the symptom. The arena numbers are the same: at the fatal decisions
the opponent led by 8 points of material on average. What decides the games happens
earlier, when the material goes (section 14). The switch stays, off.

## 14. A blind opponent model (rejected by likelihood)

**What.** Replace the one-ply Stockfish model on the true board by one-ply Stockfish on
what the opponent can see (our unseen pieces removed), since the opponents are engine-on-
belief bots that do not see our hidden pieces. If true, the belief would sharpen and the
Greek-gift bait (a hung queen protected by a hidden piece) would follow from the search.

**Result.** On 4,783 real opponent moves from 125 arena games
(`tools/arena/opp_model_calib.py`) the true-board model makes the move played 2.05x as
likely as equal odds (top-1 27%); the blind model 1.17x (top-1 12%), worse at every
temperature and in every bucket of how many of our pieces were hidden. On captures the
true-board model is at 4.8x (top-1 53%).

**Why.** The opponents' beliefs are good: they capture when Stockfish on the true board
says so. A board with our pieces removed is not what they see; what they see is a sample
of plausible placements, which behaves on average like the true board. Modelling them as
blind throws away what they know.

## 15. Two plies with the fog in them (``FOW_INFOSET``; testing)

**What.** The information-set correction at depth two (`eBotI/infoset.py`): for the best
five moves by the one-ply value, on the twelve heaviest scored states, the three likeliest
replies (same one-ply model); group the (state, reply) pairs by the view we would have
after the reply; our next move must be one move per group, chosen for the group's weighted
mean; the move's value is the mean over groups. Half the budget, depth 6 at the leaves.

**Why it should work.** Stockfish's value of a board after our move assumes we see the
reply before we move again. The expectation over boards of a maximum is at least the
maximum of the expectation (Jensen), so the one-ply value is an upper bound, loosest for
the moves that leave most of the board unseen. This is the shape of 73% of the lost games:
material, then the king, lost two to five plies after a move the engine liked, to a piece
that swung onto a line we could not see. Sections 2-11 all averaged the same biased value;
this changes the value.

**Status.** 100 games against v4 at 120+2 running (started 12:40 on 2026-11-18).

## 16. The Greek Gift study and the safe-first rule (2026-11-18, evening)

**What.** Ten replay analyses of the 2302-rated bot (`docs/greek-gift.md`). It is our
architecture: the same consistent set (its slow mode triggers at exactly 1,000 states counted
our way), an anytime root search, a view-keyed book, an engine-class evaluator that matches
Stockfish, Leela and Maia alike only 55-63% on fully known positions (deliberate randomness
among near-equal moves), no opponent-blindness model, no fog evaluation terms, a belief no
sharper than ours. The difference that is left is the decision rule: a zero-risk move
whenever one exists (97% of decisions vs our 93%; king moves 98% vs 91%). At the fatal
decision 17 of our 54 arena losses had a zero-risk move; 1 of its 11 did.

**Built.** `FOW_SAFE_FIRST=1` (any positive-risk move loses to any zero-risk move),
`FOW_EXACT_RISK=1` (risk over the whole set), `FOW_ATTACKED=1` (the x6 weight on king-attacked
states inflated our risk 2x against realized events), `FOW_BOOK=gg`, `FOW_CLOCK=reserve`,
`FOW_RANDOM` (random choice among near-equal moves), `FOW_FOG_TAX`.

**Result so far.** Safe-first against v4 at 60+1: 13-1-19 when stopped. The rule worked: at
18 of the 19 fatal decisions no zero-risk move existed. Against v4 we are hunted into
positions with no safe square before the rule can act; on the arena the losses have safe
alternatives (17 of 54), so only the arena can judge this one.

**A flaw in every local match today.** Stopping a tournament by killing its parent left the
multiprocessing workers playing the queued games; up to three tournaments ran at once and the
load average reached 35 on 10 cores. Both bots of a match were slowed alike, so no result
favours one side, but all of them had far less compute per move than the arena and more
noise than reported. A plain eBotI vs v4 control, never run before, is running on a clean
machine now.

## What is left with evidence behind it

The value, then the belief. Section 15 is the first change to the value itself.
After it, the belief: Fianchetto's ablation (RBC 2021, `docs/rbc-notes.md`) is the
one published result where a change of this kind moved a bot from 40% to 65%: a persistent
Bayesian belief with a real opponent-move model, mixed with uniform by set size, and later
tuned per opponent. Our opponents are deterministic bots with public replays, so a
per-opponent move model is possible. It is a multi-day build and the arena would have to
judge it.

## 17. Literature and the material leak (2026-11-18, night)

Two studies, both in `docs/research/`. `literature.md` reads the RBC winners (StrangeFish,
StrangeFish2, Fianchetto, Kevin, Penumbra), Obscuro and the Kriegspiel work from source: every
mean/min/CVaR/paranoia knob is neutral or negative wherever it was measured (Penumbra's grid,
Parker 2006, our own tests); what the winners add over "mean plus king risk" is material
hazard pricing (StrangeFish2's hanging-material and weak-squares terms, Fianchetto's caution,
Ciancarini's hazard model), a drained clock, a book and purified randomness. Obscuro's time
curve: +45 Elo per doubling under 1 s a move, +16 above 4 s.

`material-leaks.md` traces our 9.3 points a game lost to captures by pieces we could not see
(541 captures in 150 games) against Greek Gift's 7.8. The whole gap is quiet moves: pieces
moved onto a fog-attacked square (0.63 vs 0.22 a game) and undefended pieces left standing
under an unseen attacker (1.39 vs 0.51). Captures into the fog cost both bots the same (4.7 a
game) and net +1.5 to +3.5 over three plies, so they must not be taxed. A zero-hazard
alternative existed on the true board in 309 of our 327 moved-in cases. At equal view-only
exposure Greek Gift is hit two to three times less often: its belief, not only its rule.

Built: helper command `hang` (exact over the set, like `risk`): per candidate, the expected
pawns the opponent can take next move with a piece on a square we will not see, recapture
netted off, kings excluded. `FOW_HANG=λ` subtracts λ × that (in pawns on the tanh scale) from
every non-capturing move's value. λ = 1 is fair pricing; the data says the sampled roots
already hold part of it, and Greek Gift behaves as if λ were larger. Test: λ = 1 against v4,
150 games at 60+1, after the clock match (eBotI with the reserve clock against v4 at 180+2).
