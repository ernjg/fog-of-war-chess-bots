# Greek Gift: better belief, or the same belief with a different decision rule?

Scope: all 179 arena games of Greek Gift (v30, 8,157 of its decisions) and 125 arena games of
our v4 "Magnus Monte Carlsen" (4,807 decisions), both replayed through OUR belief
(`bots/eBotI/positions` driven by `bots/eBotI/eBotI/position_set.py`, opponent model
`eBotI/opponent.py` with 2 Stockfish engines at 0.3 s per opponent ply, cap 200,000 states),
built from the mover's own observations: initialised from its first view, updated with its
own moves and with its view after each opponent move. At every decision the helper was asked
`find <true fen>` (is the truth in the set, with what weight) and `risk 0 600 0 <k> <moves>`
(weighted share of the set in which each candidate loses the king at once; king-attacked
states weighted x6, as the search does). The <=256-state sample the search would see was
used for the king-attacked share and for the piece-safety expectations.

Scripts and raw tables (all under `scratchpad/gg2/belief/`): `replay_belief.py` (the
adapted `tools/arena/truth_risk.py`), `analyze.py` -> `analysis_tables.md`,
`deepdive.py` -> `deepdive_tables.md`, `visibility.py` -> `visibility.md`,
`replay_variants.py` (risk under other weightings) -> `variants_tables.md`;
per-decision rows in `rb_gg_*.pkl`, `rb_us_*.pkl`, `rv_*.pkl`.

"Walk-in" below = after the move, an enemy piece on a square the mover cannot see attacks
its king on the true board (the move loses at once unless the opponent misses it).

## Headline

1. **Decision rule.** On the same belief, Greek Gift takes a king risk > 0.03 while a
   zero-risk move exists in **0.8%** of such decisions (66/7,966); we do in **2.5%**
   (114/4,551). It takes *any* positive risk when a zero-risk move exists in 3.4% vs our
   7.2%; on king moves 13.4% vs 27.2%. It picks the minimum-risk candidate 95.4% of the
   time vs our 90.3% (king moves: 81.8% vs 66.9%).
2. **But that is not the whole story.** When Greek Gift does take a risk our belief can see,
   the risk does not materialise: over its 153 decisions rated > 0.03, our belief predicts
   33 walk-ins and 9 happen (realized/predicted = 0.27); over the 66 with a zero-risk
   alternative it predicts 14 and **0 happen**. For our own moves the belief is calibrated
   (257 decisions, 42 predicted, 46 realized; ratio 1.08). Something Greek Gift knows at those
   moments is not in our belief (or not in our weights; see section 1.3).
3. **Interpositions** (Q2): at the 23 decisions where Greek Gift interposed against an unseen
   checker, our belief already puts a mean weight of **0.64** on "king attacked" (>= 0.5 in
   16/23) and rates the interposing move **zero-risk in 22/23**, tied-safest with ~3.7 other
   moves. The checker is in a belief like ours; what differs is which safe move is chosen
   (it interposes, we move the king: 43 king replies vs 23 interpositions in our 76 cases).
4. **Piece safety** (Q3): under our belief, the realized rate at which the moved piece is
   attacked from the fog is the same for both bots at equal predicted hazard (e.g. predicted
   0.15-0.3: 33.9% vs 33.3%; 0.3-0.6: 54.6% vs 50.4%). Greek Gift simply plays more
   zero-hazard moves (63.0% of its moves vs 53.5%), so its moved piece is hit from the fog
   in 13.6% of moves vs our 17.3% (Q/R: 4.5% vs 7.7%). This is a decision rule, not belief.
5. **Set sizes** (Q4): in Greek Gift's games our belief is *larger*, not smaller, than in
   ours (median 1,260 vs 440 states at ply 20, 1,577 vs 218 at ply 30, 677 vs 215 at 40,
   678 vs 674 at 60) and holds the truth slightly less often (94.5% vs 96.1%). It does not
   choose revealing moves: its chosen move shows 0.12 fewer enemy pieces than the mean
   candidate, like everyone else (us -0.07, its opponents -0.13).

Hypothesis at the end.

## 1. King risk at Greek Gift's decisions (Q1)

### 1.1 Chosen move vs the safest candidate

| pop | decisions | chosen risk mean | min risk mean | chosen = min | risk > 0.03 while a zero-risk move exists | > 0.10 w/ zero-risk alt | zero-risk move exists | walked in (true board) |
|---|---|---|---|---|---|---|---|---|
| GG | 8157 | 0.0043 | 0.0009 | 95.4% | **0.8%** (66/7966) | 0.4% | 97.7% | **0.13%** (11) |
| US | 4807 | 0.0093 | 0.0026 | 90.3% | **2.5%** (114/4551) | 1.3% | 94.7% | **1.10%** (53) |

By ply band (risky choice = > 0.03 with a zero-risk alternative):

| pop | band | n | chosen risk mean | risky choice | walked in |
|---|---|---|---|---|---|
| GG | 1-20 | 1810 | 0.0009 | 0.3% | 0.0% |
| GG | 21-40 | 1797 | 0.0011 | 0.3% | 0.1% |
| GG | 41-60 | 1550 | 0.0024 | 0.5% | 0.1% |
| GG | 61-100 | 1989 | 0.0090 | 1.6% | 0.2% |
| GG | 101+ | 1011 | 0.0096 | 1.6% | 0.6% |
| US | 1-20 | 1244 | 0.0023 | 1.0% | 0.2% |
| US | 21-40 | 1156 | 0.0009 | 0.3% | 0.0% |
| US | 41-60 | 985 | 0.0120 | 3.0% | 1.3% |
| US | 61-100 | 1077 | 0.0214 | 6.4% | 2.5% |
| US | 101+ | 345 | 0.0176 | 4.0% | 3.2% |

Distribution of the chosen move's risk: GG 94.4% exactly zero, 3.0% (0,0.01], 0.7%
(0.01,0.03], 0.9% (0.03,0.1], 0.5% (0.1,0.3], 0.5% > 0.3. US: 87.9%, 4.7%, 2.0%, 2.8%,
1.9%, 0.7%. When a zero-risk move exists:

| pop | n | chose risk > 0 | > 0.01 | > 0.03 | > 0.10 |
|---|---|---|---|---|---|
| GG | 7966 | 3.4% | 1.2% | 0.8% | 0.4% |
| US | 4551 | 7.2% | 3.8% | 2.5% | 1.3% |
| GG, king moves | 753 | 13.4% | | 2.0% | |
| US, king moves | 544 | 27.2% | | 9.2% | |
| GG, belief has king attacked >= 10% | 192 | 8.9% | | 5.7% | |
| US, belief has king attacked >= 10% | 193 | 18.1% | | 9.8% | |

So on identical information Greek Gift is about 2-3x less willing to accept a visible
king risk, and the gap is largest exactly where games are lost (king moves, endgames,
suspected checks).

### 1.2 Calibration: is the risk our belief sees real?

Realized walk-ins by the risk our belief assigned to the chosen move:

| pop | bucket | n | predicted mean | expected walk-ins | realized | realized rate |
|---|---|---|---|---|---|---|
| GG | (0,0.01] | 246 | 0.002 | 0.4 | 2 | 0.8% |
| GG | (0.01,0.03] | 59 | 0.018 | 1.1 | 0 | 0.0% |
| GG | (0.03,0.1] | 72 | 0.056 | 4.0 | 5 | 6.9% |
| GG | (0.1,0.3] | 42 | 0.192 | 8.1 | **0** | **0.0%** |
| GG | (0.3,1] | 39 | 0.549 | 21.4 | **4** | **10.3%** |
| GG | all > 0 | 458 | 0.076 | 35.0 | 11 | 2.4% |
| US | (0,0.01] | 230 | 0.003 | 0.6 | 5 | 2.2% |
| US | (0.01,0.03] | 96 | 0.019 | 1.8 | 2 | 2.1% |
| US | (0.03,0.1] | 135 | 0.054 | 7.2 | 13 | 9.6% |
| US | (0.1,0.3] | 89 | 0.170 | 15.1 | 20 | 22.5% |
| US | (0.3,1] | 33 | 0.609 | 20.1 | 13 | 39.4% |
| US | all > 0 | 583 | 0.077 | 44.9 | 53 | 9.1% |

For our own moves the belief is calibrated. For Greek Gift's it over-predicts by 3-4x,
and the discrepancy sits precisely in the moves it chose freely:

| pop | subset of decisions rated > 0.03 | n | predicted mean | realized | ratio | truth in set | truth weight share | median ply |
|---|---|---|---|---|---|---|---|---|
| GG | a zero-risk alternative existed | 66 | 0.214 | **0.0%** | 0.00 | 86% | 0.094 | 74 |
| GG | no zero-risk alternative | 87 | 0.223 | 10.3% | 0.46 | 99% | 0.051 | 98 |
| GG | not actually in check | 146 | 0.207 | 3.4% | 0.17 | 93% | 0.069 | 89 |
| GG | actually in check from the fog | 7 | 0.466 | 57.1% | 1.23 | 100% | 0.038 | 98 |
| GG | king move | 62 | 0.140 | 11.3% | 0.80 | 98% | 0.058 | 110 |
| GG | non-king move | 91 | 0.272 | 2.2% | 0.08 | 90% | 0.075 | 75 |
| US | a zero-risk alternative existed | 114 | 0.164 | 12.3% | 0.75 | 95% | 0.028 | 68 |
| US | no zero-risk alternative | 143 | 0.166 | 22.4% | 1.35 | 87% | 0.031 | 82 |
| US | not actually in check | 232 | 0.149 | 14.7% | 0.99 | 93% | 0.028 | 79 |
| US | actually in check from the fog | 25 | 0.317 | 48.0% | 1.52 | 72% | 0.051 | 73 |
| US | king move | 144 | 0.136 | 25.0% | 1.84 | 90% | 0.025 | 84 |
| US | non-king move | 113 | 0.202 | 8.8% | 0.44 | 91% | 0.035 | 70 |

Under our belief, 0 walk-ins in 66 trials with a mean risk of 0.21 has probability
about e^-14. Greek Gift's "risky" moves are therefore not risky in a set it has and we do
not: when it accepts what we would call a 20-40% chance of losing the king, the true
board is never among the losing states. The truth is in our set at those decisions
(86%), with a weight share (0.094) higher than at our own risky decisions (0.028), so the
loss is not that our set lacks the truth; it is that our set keeps, with real weight, states
Greek Gift has ruled out. The 87 forced cases (no safe move) still show half the predicted
losses (10% vs 22%), while our forced cases show more than predicted (22% vs 17%).

### 1.3 Is it our weights or our set? The same moves under three weightings

The risky decisions were replayed again (`replay_variants.py`; 130 of the 153 GG and 226 of
the 257 US decisions came out > 0.03 again, the rest differ by the engine-timing noise of
the opponent model) and the chosen move's risk was asked three ways: `r600` = the search's
number (set weights, king-attacked states x6); `r100` = set weights only; `runi` = every
state in the set weighted alike, i.e. the opponent model switched off.

| pop | subset | n | r600 mean | r100 mean | runi mean | realized | expected walk-ins r600 / r100 / runi | realized |
|---|---|---|---|---|---|---|---|---|
| GG | rated > 0.03 | 130 | 0.222 | 0.116 | 0.107 | 6.9% | 28.8 / 15.1 / 13.9 | 9 |
| GG | ...with a zero-risk alternative | 53 | 0.216 | 0.110 | 0.060 | **0.0%** | 11.5 / 5.8 / 3.2 | **0** |
| GG | ...no zero-risk alternative | 77 | 0.226 | 0.121 | 0.139 | 11.7% | | 9 |
| US | rated > 0.03 | 226 | 0.185 | 0.138 | 0.135 | 20.4% | 41.8 / 31.2 / 30.6 | 46 |
| US | ...with a zero-risk alternative | 100 | 0.195 | 0.123 | 0.105 | 15.0% | 19.5 / 12.3 / 10.5 | 15 |
| US | ...no zero-risk alternative | 126 | 0.177 | 0.150 | 0.160 | 24.6% | | 31 |

Two things follow. (a) About half of the over-prediction on Greek Gift's moves is our own
weighting: the x6 boost on king-attacked states doubles the predicted risk of its moves
(28.8 -> 15.1) but barely changes ours (41.8 -> 31.2), and the opponent model adds little
either way. The states that would kill Greek Gift are states in which our weighting says
"its king is probably already attacked", and that is usually wrong for it (section 2: when it
is not in check, weight on "attacked" is 0.019). (b) A residual remains with every weighting:
with uniform weights the set predicts 13.9 walk-ins for Greek Gift and 9 happen, 3.2 and 0
for its free choices (p ~ 0.04), while for us it predicts 30.6 and 46 happen (10.5 vs 15 on
free choices). Opponents put their pieces where they attack the king more often than a
uniform draw says, as our numbers show; Greek Gift's risky moves run the other way. So it
either prunes states our set keeps, or it only accepts risk when the losing states are ones
its own weighting discounts; from outside those are the same thing. In size this is worth
3-14 expected walk-ins over 179 games (2-8% of its games), against the 17 of our 54 losses
(14% of our games) that its decision rule would have avoided on our belief.

### 1.4 Losses

| pop | losses | no zero-risk move existed | belief miss (fatal move rated < 0.01) | a zero-risk move existed and was not taken | ...of which chosen risk > 0.10 | truth in set at the fatal decision |
|---|---|---|---|---|---|---|
| GG | 11 | 10 | 2 | 1 | 0 | 11/11 |
| US | 54 | 37 | 5 | **17** | **10** | 46/54 |

Greek Gift dies cornered (10 of 11 losses: every candidate had positive risk, median ply
105, mostly at 2 s per move in time trouble). Seventeen of our 54 losses (31%) are
decision-rule failures under our own belief: a zero-risk move existed and the search took a
move rated 0.05-0.70. Per 1,000 decisions: walk-ins GG 1.3 vs US 11.0; walk-ins with a
zero-risk alternative 0.1 vs 3.5; risky choices 8.1 vs 23.7; risky choices that walked in
0.0 vs 2.9.

## 2. Interpositions against unseen checks (Q2)

Decisions where an unseen enemy piece attacks the mover's king on the true board:
GG 45 (per 181 decisions), US 76 (per 63).

| pop | reply | n | belief weight on "king attacked" (mean) | >= 0.5 | truth in set | chosen risk mean | interposing/chosen move is min-risk | rank <= 2 | survived |
|---|---|---|---|---|---|---|---|---|---|
| GG | interpose | 23 | **0.64** | 70% | 78% | 0.000 | **100%** | 100% | 100% |
| GG | king move | 19 | 0.62 | 63% | 95% | 0.092 | 79% | 95% | 89% |
| GG | unrelated | 3 | 0.39 | 33% | 100% | 0.521 | 33% | 33% | 0% |
| US | interpose | 23 | 0.51 | 57% | 91% | 0.033 | 96% | 96% | 100% |
| US | king move | 43 | 0.47 | 42% | 86% | 0.061 | 65% | 98% | 93% |
| US | unrelated | 10 | 0.38 | 30% | 80% | 0.462 | 10% | 60% | 0% |

- Our belief detects the check: when the mover is in check from the fog the mean weight on
  "king attacked" is 0.61 (GG's games) / 0.47 (ours); when not in check it is 0.02-0.03
  (>= 0.5 in only 1.8% / 2.3% of decisions). Zero weight in 1 of 45 GG cases (an8d2x1u 57).
- At GG's interpositions the interposing move has exact risk 0 in 22/23 and ranks safest;
  3.7 other moves (median 4) share rank 0 among ~34 candidates. In 5/23 the belief weight on
  check is < 0.1 (the opening ...Qa5+ answered by Nc3, c2c3 against ...Bb4: incidental,
  we play the same moves).
- When a zero-risk move existed, GG chose one in 32/33, we in 41/48. When none existed, GG
  chose the min-risk move in 7/12 and survived 8/12; we chose it in 10/28, survived 17/28.
- The 10 "unrelated" replies of ours were all fatal; in 3 of them a zero-risk move existed
  and the search took a move rated 0.27-0.70 (l8ma5ub5 71, abfstiqy 46, 47daxfz0 63).

So a belief like ours contains the checker with majority weight, and its exact risk already
marks the interposition as safe. Nothing in Greek Gift's interposition behaviour requires
a sharper belief; it requires preferring a zero-risk non-king move over a zero-risk king
move (which keeps the king home: it moves the king half as often as we do).

## 3. Piece safety (Q3)

Predicted = over the belief sample after the chosen move, expected own non-king material
(P1 N3 B3 R5 Q9) attacked by an enemy piece the mover cannot see; realized = the same on
the true board with the mover's real view.

| pop | n | fog material pred | realized | P(any) pred | realized | P(moved piece attacked from fog) pred | realized | realized, non-pawn moves | realized, Q/R moves |
|---|---|---|---|---|---|---|---|---|---|
| GG | 8157 | 1.40 | 1.55 | 0.565 | 0.619 | 0.121 | **13.6%** | 10.2% | 4.5% |
| US | 4807 | 1.46 | 1.77 | 0.600 | 0.669 | 0.154 | **17.3%** | 14.7% | 7.7% |

Realized attack on the moved piece by predicted bucket:

| bucket | GG n (share) | GG realized | US n (share) | US realized |
|---|---|---|---|---|
| = 0 | 5141 (63.0%) | 0.0% | 2572 (53.5%) | 0.0% |
| (0,0.05] | 900 (11.0%) | 4.6% | 716 (14.9%) | 4.7% |
| (0.05,0.15] | 540 (6.6%) | 14.1% | 401 (8.3%) | 15.0% |
| (0.15,0.3] | 401 (4.9%) | 33.9% | 270 (5.6%) | 33.3% |
| (0.3,0.6] | 441 (5.4%) | 54.6% | 268 (5.6%) | 50.4% |
| (0.6,1] | 734 (9.0%) | 83.7% | 580 (12.1%) | 88.3% |

Per bucket the realized rates are the same for both bots: our belief predicts the hazard
to Greek Gift's pieces exactly as well as to ours. The difference is in the distribution:
Greek Gift plays zero-hazard moves 63% of the time vs 53.5%, and high-hazard (> 0.6) moves
9.0% vs 12.1%. Its material-at-risk after the move is also realized slightly above
prediction for both (1.55 vs 1.40; 1.77 vs 1.46), i.e. our belief underestimates lurking
attackers a little, more so in our games (hanging pieces in low-weight states).

Same by phase (realized moved-piece attack): GG 16.4/19.6/15.2/8.3/5.6% in plies
1-20/21-40/41-60/61-100/101+; US 21.0/22.9/17.7/10.6/4.9%.

## 4. Set sizes and what the moves reveal (Q4)

| ply | GG median set | GG mean | GG p90 | GG truth in set | US median set | US mean | US p90 | US truth in set |
|---|---|---|---|---|---|---|---|---|
| 10 | 128 | 8720 | 19053 | 100% | 135 | 1509 | 1939 | 100% |
| 20 | **1260** | 26634 | 92931 | 91.7% | 440 | 36369 | 200000 | 94.3% |
| 30 | **1577** | 33030 | 193717 | 89.0% | 218 | 10335 | 22866 | 92.2% |
| 40 | 677 | 28286 | 125889 | 90.8% | 215 | 8976 | 9893 | 93.7% |
| 50 | 402 | 21359 | 67964 | 92.2% | 297 | 6154 | 7623 | 92.9% |
| 60 | 678 | 18769 | 44602 | 92.1% | 674 | 7790 | 10945 | 93.1% |
| 80 | 428 | 12024 | 13028 | 95.2% | 732 | 12885 | 45597 | 98.0% |
| 100 | 245 | 13218 | 21615 | 96.8% | 398 | 21044 | 23837 | 100% |

Truth in set over all decisions: GG 94.5%, US 96.1%; mean weight share of the truth when
present: GG 0.21/0.13/0.12/0.09 in plies 1-20/21-40/41-60/61-100, US 0.28/0.16/0.11/0.07.
Closed openings leave more consistent states, not fewer; our belief is if anything less
sharp in Greek Gift's games.

Enemy pieces visible in the mover's own view after its move (all 179 + 125 games; `visibility.md`):

| pop | moves | enemy pieces visible | enemy pieces on board | visible share | unseen squares | chosen - mean over candidates (visible) | max over candidates - chosen | share of candidates showing more |
|---|---|---|---|---|---|---|---|---|
| GG | 8110 | 1.69 | 10.63 | 0.159 | 28.8 | -0.12 | 1.94 | 30.4% |
| GG's opponents | 8185 | 1.49 | 11.09 | 0.134 | 31.9 | -0.13 | 1.90 | 29.3% |
| US | 4807 | 1.53 | 10.50 | 0.145 | 29.8 | -0.07 | 1.84 | 28.7% |
| our opponents | 4813 | 1.62 | 10.42 | 0.155 | 30.5 | -0.08 | 1.73 | 29.0% |

After its moves Greek Gift sees 1.69 enemy pieces (15.9% of them) against 1.49 (13.4%) after
its opponents' moves and 1.53 (14.5%) after ours; the gap comes from the middlegame (plies
21-60: 2.46/2.25 vs 2.13/1.91) and the endgame (1.21 vs 1.09), where its pieces are more
active, not from choosing revealing moves: like every bot it picks a move that shows 0.1
fewer enemy pieces than the average candidate and leaves ~1.9 fewer than the most revealing
one. There is no information-seeking in its move choice.

## 5. Hypothesis

**Same information, a stricter decision rule, and a different weighting of the set: most of
Greek Gift's edge over us is the decision rule; a second-order part is that it does not
inflate "my king may already be attacked" states the way our search does (and may prune
states we keep), which is what lets it accept 66 risks our belief calls 20% without a loss.**

Evidence for "decision rule":
- On identical information it takes a visible king risk when a safe move exists 3x less
  often than we do (0.8% vs 2.5%; king moves 2.0% vs 9.2%), picks the min-risk move more
  often (95% vs 90%), and plays zero-hazard piece moves more often (63% vs 54%).
- Its interpositions are already zero-risk and top-ranked under our belief (22/23), with the
  checker carrying 0.64 of the weight; what differs is that it prefers a safe non-king move.
- Its piece-hazard calibration under our belief is identical to ours bucket by bucket.
- One third of our losses (17/54) are moves our own belief rated risky while a zero-risk move
  existed; Greek Gift has 1 such loss in 11.
- Under our belief its consistent set is larger and holds the truth slightly less often.

Evidence for "sharper belief" (narrow but strong):
- The 153 decisions our belief rates > 0.03: predicted 33 walk-ins, 9 realized; the 66 with
  a safe alternative: predicted 14, realized 0 (p ~ e^-14 if our belief were right). For our
  own such decisions the belief is calibrated (ratio 1.08). So in exactly the situations
  where it chooses to accept a risk, Greek Gift knows the losing states are not real. The
  truth is in our set (86%) with normal weight, so the gap is in the states our set keeps
  that its set does not (or weights far lower). Half of this gap is our x6 weighting of king-attacked states (section 1.3); the rest survives uniform weighting (0 realized vs 3.2 expected on its free risky choices; ours 15 vs 10.5).
- Its opponents' pieces hit its moved piece from the fog slightly less than our belief
  predicts (ratio 1.11) against our 1.21, a small sign that its positions hide less than ours.

What would close the gap for us, in order of evidence: (1) a decision rule that never
accepts positive king risk when a zero-risk move exists and that answers suspected checks
with a safe non-king move (this alone accounts for the 17 losses and most of the 2.9 per
1,000 fatal risky choices); (2) a pruning/weighting of the set that removes the states Greek
Gift evidently discounts at its risky decisions, which is the only part of its edge that a
copy of its decision rule on our belief would not reproduce. The first concrete
candidate for (2) is the x6 boost on king-attacked states in the risk scan: on Greek Gift's
moves it doubles predicted risk without predicting anything, and on ours it mainly
over-rates forced positions; a scan at x1 (or with the boost applied only when the belief's
own weight on "attacked" exceeds ~0.1) is a one-line change to test in games.
