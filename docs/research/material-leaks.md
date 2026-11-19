# Where our 9.3 points/game to unseen captures go, and the rule that would stop the leak

Data: 150 arena games of v4 (541 unseen captures of our pieces, 9.27 pts/game) and 179 of Greek Gift (540, 7.78). Replayed with `starter/referee.py` `FowBoard`; "unseen" = the capturer's square was `?` in the victim's view before the capture. Scripts in this folder: `unseen_losses.py`, `tables.py`, `calib.py`, `calib_tables.py`, `rule.py`, `rule_tables.py`.

## The finding

**The 1.5 pts/game gap to Greek Gift is entirely undefended pieces that were not part of a capture: pieces we moved quietly onto a fog-attacked square (0.63 vs 0.22 pts/game) and, twice as big, undefended pieces we left standing while an unseen attacker bore on them (1.39 vs 0.51).** The largest single category, a capturer taken on the square it just captured on (us 4.73, GG 4.60 pts/game), is the same for both bots and is the price of the 9.2 we take: those exchanges net +1.5 to +3.5 over three plies at every exposure level, for both bots. A rule must therefore tax quiet moves and standing pieces only, never captures.

## (a) How the captured piece got there

| category (relative to our previous decision) | us n | us pts/g | us net 2 plies | GG n | GG pts/g | GG net 2 plies |
|---|---|---|---|---|---|---|
| moved_in: our move put it there, capture (exchange) | 239 | 4.73 | -4.96 | 264 | 4.60 | -4.61 |
| moved_in: our move put it there, quiet | 88 | 1.51 | -1.01 | 69 | 0.87 | -0.27 |
| left_fresh: attacker placed by the opponent's previous move, we moved something else | 96 | 1.57 | -0.99 | 94 | 1.11 | -0.25 |
| left_standing: attacker had borne on it 2+ plies, we moved something else | 113 | 1.41 | -0.71 | 110 | 1.14 | -0.37 |
| opened: our move opened the line | 5 | 0.06 | -0.04 | 3 | 0.06 | -0.02 |
| total | 541 | 9.27 | -7.70 | 540 | 7.78 | -5.51 |

Every unseen capture is an arrival from outside the view; the useful split is whether the attacker already bore on the square at our decision (left_*: 39% of our points) or only after our move (61%). In the left_* cases we had seen the attacker at decision time in 2 of 209 (GG 1 of 204): belief failures, not ignored information.

## (b) Defended or free

| | us free pts/g | GG free | us defended | GG defended |
|---|---|---|---|---|
| moved_in capture | 3.59 | 3.53 | 1.14 | 1.07 |
| moved_in quiet | 0.63 | 0.22 | 0.88 | 0.65 |
| left_fresh + left_standing | 1.39 | 0.51 | 1.58 | 1.74 |
| total | 5.64 | 4.26 | 3.62 | 3.52 |

Defended pieces cost the same; 1.38 of the 1.49 gap is free pieces, and free capturers are equal. 276 of our 541 unseen captures were real losses over two plies (net <= -2; GG 282); the rest were even or favourable exchanges.

## (c) Did it decide the game?

| | n | mean balance before | mean balance +10 plies | decisive (>= -1 before, <= -3 after) | pts/g in lost games |
|---|---|---|---|---|---|
| us moved_in | 327 | +0.6 | -2.3 | 64 (1.39 pts/g) | 3.35 |
| us left_* | 209 | -1.0 | -1.5 | 20 (0.43) | 1.60 |
| us all | 541 | 0.0 | -2.0 | 84 (1.81) | 4.99 |
| GG all | 540 | +2.7 | +1.7 | 31 (0.59) | 0.87 |

84 of our unseen losses turned a level position into -3 or worse within 10 plies, 64 of them moved_in; GG takes its losses from +2.7 and stays ahead.

## (d) Piece and phase (pts/game)

| | P | N | B | R | Q | plies 1-20 | 21-40 | 41-60 | 61+ |
|---|---|---|---|---|---|---|---|---|---|
| us | 1.45 | 3.44 | 1.46 | 2.20 | 0.72 | 1.79 | 3.17 | 2.77 | 1.55 |
| GG | 1.05 | 2.88 | 1.91 | 1.73 | 0.20 | 1.08 | 2.61 | 2.11 | 1.98 |

Knights are the biggest item (moved_in knights 2.46 vs 1.98), then queens (0.72 vs 0.20); the excess is in plies 1-60.

## Counterfactual: was there an obvious alternative?

On the true board a legal move leaving no piece of ours attacked by an unseen enemy existed in 309 of 327 moved_in cases (median 25 of 36 moves), 79/96 left_fresh, 88/113 left_standing; GG the same (320/333, 79/94, 97/110). The chosen move's true hazard averaged 2.3 points, the best alternative 0.1. The bot does not have the true board, so what does a view-only rule see?

View-only exposure L(move) = sum over our non-king pieces after the move of E(s) x (value if undefended, max(0, value-3) if defended), where E(s) sums, over unseen squares that could attack s along a ray through seen-empty or unseen squares (knight and pawn geometry included), the empirical prior P(enemy piece there | rank, phase) times the share of unaccounted enemy pieces of that kind. Calibration on quiet moves (realised loss to an unseen capture on the next ply, per move):

| L after a quiet move | us moves/g | us realised/move | GG moves/g | GG realised/move |
|---|---|---|---|---|
| < 0.5 | 13.3 | 0.06 | 18.6 | 0.06 |
| 0.5-1 | 5.6 | 0.09 | 7.7 | 0.08 |
| 1-2 | 6.5 | 0.15 | 6.2 | 0.10 |
| 2-4 | 3.5 | 0.30 | 2.4 | 0.09 |
| 4+ | 0.9 | 0.37 | 0.4 | 0.19 |

Quiet moves cost us 3.79 pts/game, GG 2.58, and 1.47 of the gap is in quiet moves with L >= 1 (us 2.39, GG 0.92): we make 1.6x more of them (4.4 vs 2.8 per game at L >= 2) and at equal L we are hit two to three times as often. Geometry explains the first part; the second says GG knows where the pieces are (belief): its pieces stand on squares that look exposed but are not. Captures calibrate alike for both bots (realised 0.6-0.8 per move at L >= 2, three-ply gain +1.5 to +2.3), so captures must not be taxed. Oracle rates for a belief tax: an undefended piece truly attacked from the fog is taken next ply 41% of the time if we just moved it (GG 49%), 29% if standing (GG 18%); one not truly attacked 0.9%/0.0%.

## The rule

For quiet (non-capturing, non-king) candidate moves: `score'(m) = score(m) - lambda * L(m)` with `L` the expected free loss above and `lambda` the calibrated hit rate (0.10 pawn per unit of the view-only L; with the belief sample, 0.4 x free loss for the moved piece and 0.3 x for standing pieces, i.e. `FOW_FOG_TAX` in `bots/eBotI/eBotI/stockfish_search.py` restricted to quiet moves). The threshold version to test first: reject a quiet move with L > 2 when a legal move with L <= 1 exists.

| threshold T | us flagged/g (share of quiet moves) | realised loss on flagged, pts/g | flagged moves' 3-ply material gain vs unflagged | GG flagged/g, loss |
|---|---|---|---|---|
| 1.0 | 5.2 (21%) | 1.12 | +0.39 vs +0.34 | 5.8, 0.39 |
| 2.0 | 3.1 (12.5%) | 0.86 | +0.24 vs +0.36 | 2.2, 0.13 |
| 3.0 | 1.7 (7%) | 0.67 | +0.22 vs +0.36 | 0.9, 0.12 |

At T = 2 the rule touches 3 quiet moves a game; they lost 0.86 pts/game to the next unseen capture, and the alternatives (mean L 0.35) would have lost about 0.1: roughly **0.75 pts/game saved, half the gap to Greek Gift** (T = 1: about 1.0). Cost: nothing on captures (the 9.2 we take is untouched) and no material cost visible in the flagged moves' three-ply gain (+0.24 vs +0.36 unflagged), so they were not setting anything up; the positional cost must come from games. Applied to captures the same rule would forgo 3.5 pts/game of captured material to save 0.65: do not.

## The urisk pickles

`urisk_us_*.pkl` and `urisk_gg_*.pkl` rows hold only game, ply, size/exact, king_move, check0, walk and the king-risk triples `u/w/w1` (value, min, zero count). Piece hazard cannot be read from them; skipped.
