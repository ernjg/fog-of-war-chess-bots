# Greek Gift's evaluation terms, inferred by conditional logit against true-board Stockfish

Scripts and data (all under `scratchpad/gg2/features/`): `extract.py` (choice sets and per-move
features, rules via `starter/referee.py`, `exposure()` copied from `bots/eBotI/eBotI/hazard.py`),
`sf_all.py` (Stockfish depth 8, MultiPV = every legal move, two engines, cache `sf_all.pkl`),
`fit.py` (Newton-Raphson conditional logit with SEs, delta-method cp conversion, held-out split;
output `fit_output.txt`), `analysis.py` (GG minus v4 with SEs, restricted choice sets, phase split,
effect sizes; output `analysis_output.txt`). The earlier `gg/ea` caches held only top-3 moves and
single after-move evals, so they could not be reused for a whole-choice-set model.

## Sample and model

50 random Greek Gift v30 games (2,135 of its decisions) and 40 random arena games of our v4
(1,651 decisions). A decision = the FoW-legal moves on the true board, minus moves that leave the
mover's own king attackable (an immediate loss; the chosen move was such a move 4 times for GG,
18 for v4, those decisions dropped), minus the rare position where Stockfish cannot be asked
(enemy king already attackable). Mean choice set 31 moves. Every alternative gets Stockfish's
depth-8 evaluation of the pre-move true board (MultiPV over all moves, mover's view, mate = +-1000
cp) and these features of the true board after the move, with the mover's view
`observation(board_after, mover)` (the replay views match this function exactly):

| feature | meaning |
|---|---|
| seen | squares in the mover's view |
| enemy_seen | enemy pieces in the mover's view |
| unseen_hang | free-capture material of the mover's pieces attacked by an enemy piece the mover cannot see (full value if undefended, else value minus cheapest such attacker when positive) |
| seen_hang | same, attackers the mover can see |
| exp_rook / exp_bishop | unseen squares with an open rook / bishop line to the mover's king (`exposure()`) |
| king_move | non-castling king move |
| castle | castling |
| capture / trap | capture; capture whose square is guarded by an enemy piece unseen before the move |
| own_visible | the mover's pieces on squares the enemy attacks, i.e. pieces the enemy can now see |
| pawn_opens | pawn move that lengthens an open ray from the mover's king |
| check, dest_att_unseen, queen | gives check; destination attacked by an unseen enemy piece; queen move |

`dest_unseen` (destination square not in the view) is identically zero under these rules and was
dropped. Model: P(move) proportional to exp(a * eval + sum b_i * f_i), fitted separately per bot.
Two eval responses were used: linear in centipawns (as specified) and a two-slope version with an
extra term `near = max(eval - best, -1 pawn)`, because both bots respond far more steeply within a
pawn of the best move than in the tail (near-best slope ~2.4/pawn vs 0.45/pawn in the tail). The
linear model is misspecified in a way that inflates the cp value of every discrete feature
(castle, capture), so cp weights are reported on three scales: all alternatives with the linear
fit (upper bound), alternatives within 3 pawns of the best (linear fit, the useful middle), and
within 1 pawn (lower bound). Signs, z-scores and the GG-v4 ordering are the same on all three.

## Coefficients in centipawns per unit (alternatives within 3 pawns of SF's best, linear fit)

GG: 1,984 decisions, a = 1.63/pawn. v4: 1,503 decisions, a = 1.49/pawn. "diff" = GG - v4, z from
delta-method SEs. `wstd` is the feature's typical spread within a decision, so cp*wstd is how much
the term actually moves a typical choice.

| feature | GG cp (se) | v4 cp (se) | diff | z | GG cp*wstd |
|---|---|---|---|---|---|
| seen (per square) | +3.7 (0.9) | +3.5 (1.1) | +0.2 | 0.2 | 6.7 |
| enemy_seen (per piece) | -1.2 (2.6) | -2.8 (3.3) | +1.5 | 0.4 | -0.7 |
| unseen_hang (per point) | +0.7 (2.8) | -5.4 (3.1) | +6.1 | 1.5 | 0.3 |
| seen_hang (per point) | -5.4 (2.3) | -5.3 (2.6) | -0.1 | 0.0 | -2.2 |
| exp_rook (per square) | -7.4 (1.5) | -7.4 (1.5) | -0.1 | 0.0 | -5.0 |
| exp_bishop (per square) | -0.7 (1.8) | -3.2 (2.2) | +2.5 | 0.9 | -0.4 |
| king_move | -16.5 (6.3) | +19.9 (7.0) | -36.4 | -3.9 | -3.9 |
| castle | +143 (14) | +156 (18) | -13 | -0.6 | 1.4 |
| capture | +37 (8) | +59 (10) | -23 | -1.7 | 4.9 |
| trap | +34 (12) | +60 (15) | -26 | -1.4 | 2.9 |
| own_visible (per piece) | -39 (5) | -24 (6) | -15 | -2.0 | -14.2 |
| pawn_opens | +10 (5) | +25 (7) | -15 | -1.7 | 2.3 |
| check | +41 (9) | +18 (12) | +23 | 1.5 | 2.1 |
| dest_att_unseen | +17 (6) | +38 (7) | -21 | -2.2 | 5.8 |
| queen | -26 (6) | -50 (9) | +24 | 2.2 | -5.6 |

Other scales, same ordering (GG / v4): all alternatives, linear, a = 1.45 / 1.16 per pawn:
king_move -31 / +31, dest_att_unseen +24 / +68, own_visible -52 / -44, pawn_opens +12 / +36,
capture +57 / +108, trap +54 / +91, check +56 / +30, queen -36 / -71, seen +5.3 / +5.8,
exp_rook -10.5 / -11.0, castle +204 / +250. Within 1 pawn of the best, a = 2.79 / 2.50:
king_move -6 / +10 (z of diff -2.5), dest_att_unseen +3 / +21 (z -2.8), own_visible -18 / -14,
pawn_opens +3 / +16 (z -2.2), capture +15 / +33, trap +25 / +42, check +32 / +14, queen -18 / -35
(z 2.1), seen +2.3 / +1.9, exp_rook -3.4 / -5.5, castle +73 / +81. Two-slope model, all
alternatives, phase split (plies 21+, where most decisions are): king_move diff z = -4.2,
dest_att_unseen z = -3.2, queen z = +2.9, capture z = -2.2, check z = +1.7; everything else |z| < 1.6.

## Held-out validation (25% of games by game id, fitted on the rest)

GG, 549 decisions in 12 games; v4, 427 decisions in 10 games. LL per decision (higher is better)
and top-1 accuracy of the fitted model's argmax.

| model | GG LL | GG top-1 | v4 LL | v4 top-1 |
|---|---|---|---|---|
| uniform over legal moves | -3.300 | 0.03 | -3.345 | 0.03 |
| raw Stockfish argmax | | 0.279 | | 0.227 |
| (a) Stockfish only, linear | -2.457 | 0.337 | -2.511 | 0.335 |
| (b) Stockfish + 11 base features, linear | -2.361 | 0.330 | -2.397 | 0.342 |
| (a') Stockfish only, two-slope | -2.322 | 0.337 | -2.379 | 0.335 |
| (b') Stockfish + 16 features, two-slope | -2.246 | 0.350 | -2.274 | 0.389 |

The features are real (likelihood-ratio chi2 = 425 on 11 df in-sample for GG, 411 for v4) but
small: they add 0.07-0.10 nats per decision, a perplexity of 10.1 -> 9.5 among ~31 moves, and at
most 1.3 points of top-1 for GG. Two thirds of GG's deviation from true-board Stockfish is not
explained by any of these terms. The natural reading: GG, like v4, evaluates a belief about the
board, and the belief, not an extra evaluation term, drives most of the disagreement with the true
board. Note also that the eval slope is almost the same for the two bots (GG 1.45 vs 1.16 per
pawn linear; 2.43 vs 2.34 near-best): GG is not a sharper Stockfish than we are.

## What the coefficients say

1. The hypothesised Fog-of-War terms are NOT what separates Greek Gift from v4. Vision (+3.7 vs
   +3.5 cp per seen square), enemy pieces seen (0 for both), seen-attacker hanging material (-5.4 vs
   -5.3 per point), rook-ray king exposure (-7.4 vs -7.4 per unseen square), bishop-ray exposure
   (about 0 for both), castling (+143 vs +156): identical within one standard error on every scale.
   Both bots show the same mild preference for seeing more and for a king without unseen rook rays.
   For v4 these can only be by-products of averaging Stockfish over sampled boards (a sampled
   board with an enemy rook on the unseen ray scores badly), so the same numbers for GG mean GG
   gets them the same way, not from explicit terms. Piece safety against unseen attackers is
   even slightly weaker for GG (+0.7 vs -5.4 cp/point, z 1.5): relative to the true board it
   hangs material into the fog no more and no less than Stockfish allows, i.e. its belief already
   knows where the unseen attackers are.

2. Where GG differs, with sign and significance stable across every specification:
   - King moves. GG penalises a non-castling king move by about 16 cp (6 to 31 depending on
     scale) beyond Stockfish; v4 rewards one by about 20 cp (10 to 31). The difference is the
     largest and most significant in the study (z = -3.9 to -4.5). This matches the earlier
     finding that v4 moves its king 17% of the time against Stockfish's 11%, and that our losses
     come from king moves into unseen attackers.
   - Moving onto a square attacked by an unseen enemy piece. True-board Stockfish already knows
     the attacker, so a positive coefficient measures how blind the bot is. v4: +38 cp (+21
     within a pawn of best, z of diff -2.2 to -3.2); GG: +17 (+3 within a pawn). GG behaves
     almost as if it could see the attacker. This is a belief quality effect or an explicit
     penalty on destinations that could be attacked from the fog; from the outside they are the
     same thing.
   - Capturing. v4 captures 59 cp more eagerly than Stockfish, GG 37; captures into an unseen
     recapture ("trap"): v4 +60, GG +34. Again GG is closer to the true board.
   - Keeping pieces out of the enemy's sight. Each own piece standing on an enemy-attacked square
     (hence visible to the enemy) costs GG 39 cp, v4 24 (z -2.0). Scaled by its spread this is
     GG's largest non-eval term (14 cp per typical decision).
   - Pawn moves that open a line toward its own king: GG +10, v4 +25 (z -1.7 to -2.2). v4's
     e-pawn openings and f/g pushes are partly a preference beyond Stockfish; GG's are not.
   - Checks: GG +41, v4 +18 (z 1.5 to 1.8). GG gives more checks than Stockfish wants; its wins
     come from opponents mishandling checks from unseen pieces.
   - Queen moves: both bots avoid them relative to Stockfish (another belief-averaging by-product,
     a queen into fog is risky across samples), GG less so (-26 vs -50, z 2.2).

## Terms that would make a Stockfish-on-belief bot play like Greek Gift

v4 has no explicit Fog-of-War terms; everything above is implicit in belief averaging. Adding the
following terms on top of our belief-averaged Stockfish score moves each coefficient from v4's
value to GG's (GG minus v4, on the within-3-pawn scale; the within-1-pawn scale is roughly half,
the all-alternatives linear scale roughly three times):

| term | weight (cp) | note |
|---|---|---|
| non-castling king move | -35 | biggest, most certain; v4 currently likes king moves |
| destination attacked by an enemy piece we cannot see (attacked in a material share of belief samples) | -20 | or equivalently: a sharper belief about unseen attackers |
| each own piece on a square the enemy attacks (visible to it) | -15 | per piece, after the move |
| capture | -20 | and a further -25 when the captured square is guarded in the fog |
| pawn move that opens a ray from our king | -15 | |
| giving check | +20 | |
| queen move | +25 | i.e. remove most of the queen aversion belief averaging creates |

Terms we do not need to add, because GG does not have them beyond what v4 already does
implicitly: vision (seen squares, enemy pieces seen), unseen-attacker hanging material, rook or
bishop ray exposure, castling bonus. Closedness was only measured through `pawn_opens`; the
closed-opening difference found earlier is an opening book, not a per-move preference.

Which of the seven we lack: all of them. None exists in `fow/obscuro`, and the sign of our implicit
king-move, capture and unseen-destination behaviour is the wrong one. The honest caveat is in the
validation: even with every term, Stockfish-on-the-true-board explains GG's move only a third of
the time, and the terms raise that by one point. Most of the remaining gap is which board GG
believes it is looking at, which this method cannot see. The terms above are what is visible
from the outside; the king-move and unseen-destination ones are also exactly where our games are
lost, so they are the ones to test with games first.
