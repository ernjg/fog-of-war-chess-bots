# Greek Gift v30: think time as a side channel into its algorithm

Data: 179 arena games (180 s + 2 s), 8175 Greek Gift moves. For every move our own tracker (`bots/eBotI/eBotI/position_set.py`
driving `bots/eBotI/positions`, cap 200000, `policy=None`) replayed Greek Gift's observations and counted the positions
consistent with them; 5347 rows have an exact count, 2828 are after the cap cut the set (count unreliable). Scripts in this
folder: `extract_feats.py` (replay, one row per move -> `feats_all.pkl`), `analyze.py` (all tables -> `analysis_out.md`),
`dedup_check.py` (recount of borderline sets ignoring en passant -> `dedup.pkl`). Run with `uv run python -P`.
Think = clock before - clock after + 2, as in `../../gg/time.md`.

## Summary

Greek Gift's clock use is a closed-form, deterministic time manager with no per-position cost:

    budget = 2 + (clock - 2) / D(ply)                      D(ply): 42.5 at ply 1, -0.34 per ply to ~25 at ply 50, flattening to ~16 by ply 90
    if |consistent positions| >= 1000:  budget *= 1.5       (count by board + castling rights, en passant ignored)
    if only one move keeps the king off an attacked square: budget *= 0.5
    think = min(budget, clock / 6)                           (this cap is what the earlier report saw as a "12 s reserve")
    book move (0.3 s) in a few opening views; 2.0 s flat once the clock is at 12 s

- The slow mode is the size of the consistent position set and nothing else. On the 4305 moves where our count is exact,
  "slow iff size >= 1010" agrees on 99.4%; every one of the 27 exceptions is a normal-speed move whose set has 1022-1362
  states *including en-passant duplicates*; recounting those sets by (board, castling) ignoring en passant gives
  **slow iff count >= 1000 with 0 exceptions in the 309 sets between 900 and 2000 states**. Hidden enemy pieces, legal
  moves, view change and unseen squares explain nothing once size is known (logistic deviance 5203 -> 153 with log size
  alone, -> 4667 with the other four together, -> 95 with all five; within a size band P(slow) is 0.00 or 1.00 whatever
  the other variables). The earlier report's "view did not change" and "hidden pieces" effects are proxies for set growth.
- The multiplier is exactly 1.5 (median 1.500, p5-p95 1.498-1.502, identical from 1000 to 200000+ states): it is a
  doubled-or-not budget, not a per-sample cost. Within a mode the residual of think against the formula has sd 0.007 s
  (normal) / 0.016 s (slow), and correlates with nothing (|r| < 0.2 with set size, legal moves, captures, hidden pieces,
  fog check; binned means within +-0.005 s). A fixed budget means an anytime search; it does not run "one engine call per
  sampled board".
- The ~0.3 s moves are an opening book keyed on what it sees, with a stochastic entry: 155 moves, 143 of them at its own
  moves 5-9 with 31-38 legal moves and set sizes of 9 to 200000 (only one with a single consistent position; none forced).
  Twelve typical replies (e8g8, f8g7, b8d7, c8f5, d7d6, e7e6, d7d5, ...) make up most of it. The same (colour, ply, view)
  key is answered by the same move in most games (68 of 102 keys fully consistent) but the *same key is sometimes searched
  for 6-9 s instead* (11 mixed keys), so the book is consulted with some probability or has several lines per view.
- The two slowest moves of each game are simply the slow mode at the top of the schedule: 327 of 358 are slow-mode moves
  at own moves 3-15 with ~150 s on the clock and median 3204 consistent states (325 of 358 with >= 1000); none is a fog
  check, 45 are captures, 333 have no material swing. The two highest-ratio moves per game are all 1.50x; there is no
  third regime above it.

## 0. The time formula, refitted

The earlier fit `think = 2 + (clock - 12)/D(n)` used mostly early plies, where the clock hardly varies at a given move.
Using all normal-mode moves (exact set < 300 states) and scanning the reserve R in `think = 2 + (clock - R)/D`, the
within-ply spread of D (p90-p10 over median, where the clock varies by up to 2x at a given ply) is 0.0129 at R=0,
**0.0046 at R=2**, 0.0085 at R=3, 0.082 at R=12. So the budget is one increment plus a share of the clock above one
increment, and D depends on the **ply** (white and black at the same own move number differ by exactly one ply step),
not on pieces, material or clock:

| ply | k | D(ply) median | p10 | p90 |
|---|---|---|---|---|
| 1 | 91 | 42.46 | 42.42 | 42.50 |
| 2 | 90 | 42.09 | 42.05 | 42.14 |
| 3 | 91 | 41.68 | 41.65 | 41.72 |
| 4 | 41 | 41.32 | 41.30 | 41.37 |
| 5 | 91 | 40.93 | 40.90 | 40.97 |
| 6 | 54 | 40.55 | 40.53 | 40.59 |
| 7 | 88 | 40.17 | 40.14 | 40.21 |
| 8 | 43 | 39.80 | 39.78 | 39.84 |
| 9 | 81 | 39.41 | 39.39 | 39.45 |
| 10 | 22 | 39.05 | 39.03 | 39.11 |
| 15 | 43 | 37.32 | 37.29 | 37.37 |
| 20 | 20 | 35.63 | 35.61 | 35.67 |
| 25 | 38 | 33.95 | 33.91 | 34.00 |
| 30 | 18 | 32.26 | 32.23 | 32.37 |
| 35 | 47 | 30.59 | 30.54 | 30.66 |
| 40 | 21 | 28.88 | 28.86 | 28.94 |
| 45 | 33 | 27.22 | 27.17 | 27.28 |
| 50 | 21 | 25.52 | 25.49 | 25.62 |
| 55 | 31 | 24.02 | 23.96 | 24.07 |
| 60 | 13 | 22.51 | 22.45 | 22.53 |
| 65 | 22 | 21.18 | 21.12 | 21.26 |
| 70 | 9 | 19.86 | 19.79 | 19.89 |
| 75 | 15 | 18.70 | 18.66 | 18.77 |
| 80 | 12 | 17.61 | 17.56 | 17.69 |
| 85 | 17 | 16.91 | 16.85 | 16.98 |
| 90 | 9 | 16.40 | 16.33 | 17.15 |
| 95 | 9 | 15.79 | 15.71 | 16.11 |
| 105 | 4 | 16.67 | 14.88 | 19.86 |


D(ply) is 42.8 - 0.34 ply up to ply ~50 (0.675 per own move), then bends and flattens to ~16 by ply 90 (a quadratic
43.3 - 0.42 ply + 0.0013 ply^2 fits the medians to 0.3). The within-ply spread is 0.1%.

Slow mode is the normal budget times 1.5 at every move number, with no drift and no dependence on the set size:

| own move n | k | think / normal prediction, median | p5 | p95 |
|---|---|---|---|---|
| 4 | 15 | 1.500 | 1.499 | 1.500 |
| 10 | 63 | 1.500 | 1.498 | 1.501 |
| 20 | 65 | 1.501 | 1.498 | 1.502 |
| 30 | 40 | 1.501 | 1.496 | 1.502 |
| 34 | 36 | 1.499 | 1.325 | 1.502 |
| 36 | 29 | 1.389 | 1.165 | 1.502 |

| set size | k | multiplier median | p10 | p90 |
|---|---|---|---|---|
| [1, 1000) (inexact counts) | 193 | 1.501 | 1.498 | 1.502 |
| [1000, 3000) | 514 | 1.500 | 1.498 | 1.501 |
| [3000, 10000) | 538 | 1.500 | 1.498 | 1.501 |
| [10000, 30000) | 397 | 1.500 | 1.499 | 1.502 |
| [30000, 100000) | 314 | 1.500 | 1.499 | 1.502 |
| [100000, 200001) | 458 | 1.501 | 1.499 | 1.502 |

The fall-off after move 34 is a cap, not a third mode: over all 8020 moves with think >= 1 s, think * 6 / clock never
exceeds 1.007, and on the 883 moves that fit neither 1.0x nor 1.5x (all at clock <= 30 s or ply >= 90) it is 0.994-1.000.
So `think = min(budget, clock/6)`. At clock 12 the cap equals the increment, which is why the clock never drops below
12.0 s and why the long games end at exactly 2.00 s per move: the "12 s reserve" is emergent, not a parameter.
With mode from the exact count (>= 1010 -> 1.5x) and the cap, the formula reproduces 5051 exact-count moves with median
absolute error 0.003 s and only 31 errors above 0.1 s: 27 are the en-passant borderline sets below (fixed by the recount)
and 4 are the half-budget moves next.

Half budget: six moves took exactly 0.5x the budget (0.498-0.501; one at 0.75 = 0.5 x 1.5). All six are king moves out of
a visible check in positions where exactly one legal move leaves the king on an unattacked square (afz8s2ka ply 65 f1e1,
jk2b9wwa 58 d7e8, k1uhkbuq 15 e1e2, l3qqr2x9 52 g8g7, m3441wsf 51 g1g2, mrctmykd 38 g8h8). Of the 87 moves made in
visible check, the other 81 took the normal 1.0x or 1.5x; a check as such does not change the budget (fog check: 32
moves, all 1.0x or 1.5x). One position with a single safe king move (a297omqs ply 51) got the full budget, so the half
budget is probably a search that stops early when one root move dominates, not a rule on the move count.

## 1. What selects the slow mode

Moves with clock > 20 s, own move >= 2, classified normal (0.93-1.07x) or slow (1.43-1.57x): 5967; 4305 of them with
an exact set count.

P(slow) by consistent-set size, exact rows:

| set size | k | P(slow) |
|---|---|---|
| 1 | 288 | 0.000 |
| 2-9 | 431 | 0.000 |
| 10-99 | 1146 | 0.000 |
| 100-299 | 573 | 0.000 |
| 300-499 | 284 | 0.000 |
| 500-699 | 140 | 0.000 |
| 700-899 | 112 | 0.000 |
| 900-999 | 42 | 0.000 |
| 1000-1099 | 32 | 0.719 |
| 1100-1299 | 65 | 0.692 |
| 1300-1999 | 171 | 0.994 |
| 2000-9999 | 506 | 1.000 |
| 10000-99999 | 456 | 1.000 |
| >= 100000 | 59 | 1.000 |

Best single threshold on our raw count: slow iff size >= 1010, 27 misfits of 4305 (99.37%); no slow move has a count
below 1010, all 27 misfits are normal-speed moves with 1022-1362 states, and every one of them has en passant possible
in some state. Our helper keeps en-passant variants as distinct states; recounting the 309 exact sets with 900-2000
states after dumping them (`dedup_check.py`):

| count | best threshold | misfits of 309 | misfits at exactly 1000 |
|---|---|---|---|
| our raw count (board, castling, ep) | 1006 | 27 | 30 |
| board + castling, en passant ignored | **1000** | **0** | **0** |
| board only (castling ignored too) | 995 | 8 | 8 |
| board + ep, castling ignored | 1006 | 34 | 37 |

So Greek Gift keeps the set of consistent positions keyed on board and castling rights, and switches to the 1.5x budget
when that set reaches 1000 positions. Per game, the first slow move coincides with the first move at which our count
reaches 1000 in 149 of 168 games (the rest are off by one or more moves because our count was cut by the cap earlier).

The other candidate variables, exact rows:

| variable | P(slow) across its range |
|---|---|
| hidden enemy pieces | 0-2: 0.00 (k=26), 3-5: 0.07 (450), 6-8: 0.25 (1024), 9-11: 0.37 (1013), 12-13: 0.46 (724), 14-16: 0.25 (1068) |
| legal moves | <10: 0.23 (13), 10-19: 0.06 (150), 20-29: 0.15 (935), 30-39: 0.35 (1640), 40-49: 0.35 (1284), 50+: 0.30 (283) |
| unseen squares | <15: 0.00 (28), 15-19: 0.24 (220), 20-24: 0.34 (1161), 25-29: 0.35 (1658), 30-34: 0.25 (813), 35+: 0.09 (425) |
| view changed after the opponent's move | yes: 0.19 (2299), no: 0.41 (2006) |

Logistic regression of slow on each variable, exact rows (null deviance 5203):

| variable | coef | se | deviance | accuracy | McFadden R2 |
|---|---|---|---|---|---|
| log10 set size | 39.1 | 4.4 | 153 | 0.990 | 0.971 |
| hidden enemy pieces | 0.073 | 0.009 | 5143 | 0.708 | 0.012 |
| legal moves | 0.038 | 0.004 | 5096 | 0.702 | 0.021 |
| view changed | -1.12 | 0.07 | 4936 | 0.708 | 0.051 |
| unseen squares | -0.045 | 0.006 | 5146 | 0.708 | 0.011 |
| own move number | -0.008 | 0.003 | 5196 | 0.708 | 0.001 |
| pieces on board | 0.054 | 0.006 | 5104 | 0.708 | 0.019 |

All four non-size variables together: deviance 4667, accuracy 0.72. All five: deviance 95, accuracy 0.995; the size
coefficient is 63 per decade (se 9) and the implied 50% point of the size-only model is 10^3.04 = 1087 (the logistic
curve is a soft version of the step at 1000). Within size bands nothing else matters:

| size band (exact) | k | P(slow) | view changed | not changed | hidden <= 8 | 9-11 | >= 12 |
|---|---|---|---|---|---|---|---|
| 100-499 | 857 | 0.000 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 500-999 | 294 | 0.000 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 1000-1999 | 268 | 0.888 | 1.00 | 0.81 | 0.88 | 0.96 | 0.83 |
| 2000-9999 | 506 | 1.000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(The 0.81-0.96 cells in the 1000-1999 band are the en-passant borderline cases above.) Over all rows including the
2828 whose count our cap had cut, the agreement drops to 94.6% and the logistic R2 to 0.71, entirely from rows where our
count is a lower bound (194 slow moves with a count of 128 = our helper's refill pool, etc.); those rows cannot test the
rule. Their mode is still consistent with it: a set that once exceeded 200000 states is above 1000 for Greek Gift too.

## 2. Does the time within a mode carry any further signal?

No. Residual = think - formula (normal: 1.0x budget, slow: 1.5x budget), clock > 20 s:

| mode | k | residual mean | sd | median abs | p5 | p95 |
|---|---|---|---|---|---|---|
| normal | 3553 | 0.000 | 0.007 | 0.003 | -0.009 | +0.006 |
| slow | 2414 | -0.001 | 0.016 | 0.004 | -0.011 | +0.008 |

| variable | normal: Pearson r / Spearman / binned means | slow: Pearson r / Spearman / binned means |
|---|---|---|
| log10 set size | +0.09 / +0.16 / -0.001 .. +0.001 s | +0.10 / +0.16 / -0.002 .. +0.001 s |
| legal moves | -0.00 / +0.09 / 0.000 .. +0.001 | +0.13 / +0.16 / -0.006 (20-29) .. +0.002 (50+) |
| captures available | +0.05 / +0.15 / 0.000 .. +0.002 | +0.13 / +0.21 / -0.004 (0) .. +0.004 (5+) |
| best capture value | -0.00 / +0.11 / 0.000 | +0.07 / +0.16 / -0.004 .. +0.001 |
| hidden enemy pieces | -0.10 / -0.08 / +0.002 .. 0.000 | +0.13 / -0.07 / -0.016 (k=47) .. 0.000 |
| view changed | +0.02 / +0.07 / 0.000 | +0.01 / +0.11 / -0.001 |
| fog check | -0.02 / -0.03 / -0.002 (k=22) | -0.01 / -0.04 / -0.002 (k=10) |
| clock | -0.16 / -0.17 / +0.003 (20-60 s) .. 0.000 | +0.11 / -0.23 / -0.004 (20-60 s) .. 0.000 |

OLS of the residual on log size + legal moves + captures + clock: R2 0.03 (normal) and 0.04 (slow); the size coefficient
is 0.0005-0.002 s per decade. The largest systematic effect anywhere is ~5 ms. The time is a fixed budget set before the
search (the only quantities that matter are the clock, the ply and whether the set has 1000+ positions): an anytime
search that runs to its deadline. A cost proportional to the number of sampled boards, or to legal moves x boards, is
ruled out at the 10 ms level. The clock is read with ~10 ms granularity; think is identical to 0.01 s across games with
the same observations.

## 3. The 0.30 s moves

155 moves under 1 s: think quantiles 0.03 / 0.13 / 0.30 / 0.31 / 0.33 s (p0/p10/p50/p90/p100); white ones are
0.06-0.30 s, black ones 0.20-0.31 s. Set size at those moves: 1 once, 9 (5 times), 44-180 (15 times), the rest 290 to
200000+ (115 with an exact count); only one was fully determined. Legal moves: 9-55, median 34; none forced. 14 are
captures, 1 is a fog check, 40 follow a view change. They sit at own moves 5 (45), 6 (44), 7 (20), 8 (12), 9 (6),
then 1-4 per move up to move 23. Moves: e8g8 15, f8g7 14, b8d7 9, c8f5 9, d7d6 8, e7e6 8, d7d5 8, e7e5 5, a7a5 5, f1c4 5,
c8d7 4, b8c6 4. Games with many: cmpp8ys6 (19 of 23 moves, vs Knight Vision), m9ajv66u (14, Knight Vision), xn0i0st0
(6), i33669ij (5), seven games with 4.

Keys: 102 of the 155 share their (colour, ply, view) with another game; in 68 of those keys every game replied with the
same move. 61 have an earlier game (by creation time) with the identical observation sequence; the earlier game gave the
same reply in 52 and was itself quick in all 61. Of the 194 (colour, ply, view) keys at plies 5-23 shared by >= 2 games,
28 contain a quick move, 6 (with >= 3 games) are quick in every game, and 11 mix quick and searched replies:

| ply | colour | games: move (think) |
|---|---|---|
| 10 | black | 2q9kqwo1: d7d6 (0.30), 70i3cc0s: d7d6 (0.30), 0t74zrx0: d7d6 (0.30), iuuh35uj: d7d6 (8.96), 927w8ehb: d7d6 (0.30), wgnkkvkz: d7d6 (0.30), i33669ij: d7d6 (0.30) |
| 12 | black | 2q9kqwo1: b8d7 (0.31), 0t74zrx0: b8d7 (0.30), iuuh35uj: e7e5 (8.80), 927w8ehb: b8c6 (0.31), wgnkkvkz: b8c6 (0.30), i33669ij: b8c6 (0.30) |
| 10 | black | d42u2qjh: c8f5 (0.13), wm27pl2o: c8f5 (0.13), dukhq8lu: c8f5 (0.20), y9sa8t4u: c8f5 (0.20), 8o58b0xu: e7e6 (6.13), vdua6oh7: c8f5 (0.17), 2hxo00oz: c8f5 (0.13), 7yrrmn79: c8f5 (0.14), 2v6mg4ha: c8f5 (0.13), cmpp8ys6: e7e6 (0.30) |
| 14 | black | 2oqyl04l: b8d7 (0.30), uwyl0705: b8d7 (0.30), wtlwy1lc: b8d7 (9.56), xn0i0st0: b8d7 (0.30), nb0p6sxv: b8d7 (0.30), ekp4au52: b8d7 (0.30), n9bu38xz: b8d7 (0.30) |
| 14 | black | 4zxokkwy: f7f5 (8.98), cmpp8ys6: g8e7 (0.30) |
| 11 | white | huj29uxm: b1d2 (6.07), cknp9cih: b1d2 (6.07), 50h61idz: f4g3 (0.08) |
| 12 | black | vuydt449: g8f6 (9.15), 8o58b0xu: f8d6 (9.13), cmpp8ys6: f8d6 (0.30) |
| 14 | black | 927w8ehb: e7e5 (9.31), i33669ij: e7e5 (0.31) |
| 11 | white | yje67p3d: e2e3 (0.03), m3441wsf: e2e3 (6.06), toqmp7ys: e2e3 (0.04), 9dd5ufq0: e2e3 (6.07) |
| 13 | white | yje67p3d: f1d3 (0.19), 9noy6mzf: g1f3 (6.03), m3441wsf: g1f3 (6.03), toqmp7ys: f1d3 (0.21), 9dd5ufq0: g1f3 (6.03) |
| 15 | white | adcvfumo: g1f3 (6.00), yje67p3d: a1c1 (0.30) |


Reading: a book keyed on the view (or the own-move sequence plus view), consulted with some probability or with a
random choice among several lines; when the book hits, the reply is instant and the move after it is on the normal
schedule (ratio of the next own move: 1.0 or 1.5 as usual). The 0.03-0.2 s white entries vs 0.30 s black entries, and the
flat 0.30 s, suggest a fixed small sleep or a probe of the engine rather than a lookup alone. The moves are standard
development (castling, fianchetto, Nbd7, Bf5), the same families as its searched replies at those plies.

Full list (prior seq = earlier games with the identical observation sequence: same reply / total; view = the 64-char
view before the move, a1 first):

| game | opp | ply | n | clock | think | move | size | exact | legal | same-view games | same reply | prior seq (earlier games: same reply / total) | quick in prior? | view |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 489n97vi | Instructors | 10 | 5 | 163 | 0.16 | c8d7 | 163 | 1 | 38 | 1 | 1 | - | - | ???????????P???????-???-?-?--?-?--?-------n--n--pp--ppppr-bqkb-r |
| 489n97vi | Instructors | 12 | 6 | 165 | 0.30 | e7e5 | 1268 | 1 | 33 | 0 | 0 | - | - | ???????????????????????-?-?--?-?--?-------n?-n--pp-bppppr--qkb-r |
| ckvmtjj1 | Cross-Register | 11 | 6 | 156 | 0.30 | c1e3 | 1658 | 1 | 39 | 0 | 0 | - | - | R-BQK--RPPP--PPP--NB-N-----PP---?-?-p?-?-??????-???????????????? |
| ckvmtjj1 | Cross-Register | 13 | 7 | 158 | 0.30 | f3d4 | 1552 | 1 | 43 | 0 | 0 | - | - | R--QK--RPPP--PPP--NBBN-----pP---?-?--?-?-??????-???????????????? |
| 2oqyl04l | Strongly Invis | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | - | - | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| 2oqyl04l | Strongly Invis | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | - | - | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| 2oqyl04l | Strongly Invis | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 32 | 6 | 6 | - | - | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbq-rk- |
| 2oqyl04l | Strongly Invis | 16 | 8 | 165 | 0.30 | a7a5 | 200000 | 0 | 27 | 3 | 3 | - | - | ????????????????????????????-?-?---p-?----p?-np-pp-nppbpr-bq-rk- |
| uwyl0705 | Cross-Register | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | - | - | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| uwyl0705 | Cross-Register | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | - | - | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| uwyl0705 | Cross-Register | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 32 | 6 | 6 | - | - | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbq-rk- |
| zaguz1ig | Cranberry Lemo | 10 | 5 | 160 | 0.30 | g8f6 | 17908 | 1 | 33 | 0 | 0 | - | - | ???????????????????????-???P??-?---p------p---p-pp--ppbprnbqk-nr |
| 2q9kqwo1 | Cranberry Lemo | 10 | 5 | 157 | 0.30 | d7d6 | 11506 | 1 | 25 | 6 | 6 | - | - | ????????????????????????????P?-?-----?-------np-ppppppbprnbq-rk- |
| 2q9kqwo1 | Cranberry Lemo | 12 | 6 | 159 | 0.31 | b8d7 | 101426 | 1 | 32 | 5 | 1 | - | - | ???????????????????????-????P?-?-----------p-np-ppp-ppbprnbq-rk- |
| 2q9kqwo1 | Cranberry Lemo | 14 | 7 | 161 | 0.30 | e7e5 | 200000 | 0 | 27 | 1 | 1 | - | - | ????????????????????????????P?-?-----?-----p-np-pppnppbpr-bq-rk- |
| d42u2qjh | IAmAVirus | 10 | 5 | 163 | 0.13 | c8f5 | 290 | 1 | 31 | 9 | 7 | - | - | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| d42u2qjh | IAmAVirus | 12 | 6 | 165 | 0.28 | e7e6 | 519 | 1 | 38 | 6 | 6 | - | - | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| r340htvx | Strongly Invis | 10 | 5 | 160 | 0.30 | f8g7 | 25097 | 1 | 32 | 1 | 1 | - | - | ???????????????????????-????P?-?----------pp-np-pp--pp-prnbqkb-r |
| r340htvx | Strongly Invis | 12 | 6 | 162 | 0.30 | e8g8 | 172193 | 1 | 35 | 1 | 1 | - | - | ???????????????????????-????P?-?----------pp-np-pp--ppbprnbqk--r |
| r340htvx | Strongly Invis | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 33 | 0 | 0 | - | - | ???????????????????????-????P?-?----------pp-np-pp--ppbprnbq-rk- |
| r340htvx | Strongly Invis | 16 | 8 | 165 | 0.30 | e7e5 | 200000 | 0 | 29 | 0 | 0 | - | - | ????????????????????????????P?-?-----?----pp-np-pp-nppbpr-bq-rk- |
| m6750mh5 | Farsight | 11 | 6 | 159 | 0.08 | f1c4 | 9 | 1 | 38 | 4 | 4 | - | - | R-BQKBNRPPP---PP--N--------Pp---?-?-??---??????-???????????????? |
| wm27pl2o | Team 319 | 10 | 5 | 163 | 0.13 | c8f5 | 290 | 1 | 31 | 9 | 7 | 1/1 | 1 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| wm27pl2o | Team 319 | 12 | 6 | 165 | 0.30 | e7e6 | 519 | 1 | 38 | 6 | 6 | 1/1 | 1 | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| yliah8jb | RATIRL | 11 | 6 | 159 | 0.20 | b1c3 | 335 | 1 | 39 | 1 | 1 | - | - | RN-QKBNRPP---PPP----P------P-B--?-??-?---??-???-??p????????????? |
| pm3e1zaq | RATIRL | 14 | 7 | 149 | 0.32 | d7d6 | 200000 | 0 | 25 | 1 | 1 | - | - | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| pm3e1zaq | RATIRL | 16 | 8 | 151 | 0.30 | a7a6 | 200000 | 0 | 32 | 1 | 1 | - | - | ???????????????????????-????-?-?-----------p-np-ppp-ppbprnbq-rk- |
| pm3e1zaq | RATIRL | 18 | 9 | 152 | 0.31 | b8c6 | 200000 | 0 | 31 | 0 | 0 | - | - | ???????????????????????-????-?-?--------p--p-np--pp-ppbprnbq-rk- |
| d8kw99qn | Crimson Fog | 10 | 5 | 160 | 0.30 | c8f5 | 15684 | 1 | 31 | 11 | 0 | 0/1 | 1 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| wtlwy1lc | TUM | 10 | 5 | 163 | 0.30 | f8g7 | 11280 | 1 | 31 | 11 | 10 | - | - | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| wtlwy1lc | TUM | 12 | 6 | 165 | 0.30 | e8g8 | 79317 | 1 | 34 | 8 | 8 | - | - | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| sv1hfm94 | Next | 10 | 5 | 163 | 0.14 | c8d7 | 163 | 1 | 38 | 1 | 1 | 1/1 | 1 | ???????????P???????-???-?-?--?-?--?-------n--n--pp--ppppr-bqkb-r |
| xn0i0st0 | ADARSH | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 1/1 | 1 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| xn0i0st0 | ADARSH | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | 1/1 | 1 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| xn0i0st0 | ADARSH | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 32 | 6 | 6 | 1/1 | 1 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbq-rk- |
| xn0i0st0 | ADARSH | 16 | 8 | 165 | 0.30 | a7a5 | 200000 | 0 | 27 | 3 | 3 | 1/1 | 1 | ????????????????????????????-?-?---p-?----p?-np-pp-nppbpr-bq-rk- |
| xn0i0st0 | ADARSH | 18 | 9 | 167 | 0.31 | f8e8 | 200000 | 0 | 26 | 0 | 0 | - | - | ????????????????????????????-?-?p--p-?----p?-np--p-nppbpr-bq-rk- |
| xn0i0st0 | ADARSH | 20 | 10 | 169 | 0.30 | f6h5 | 200000 | 0 | 27 | 0 | 0 | - | - | ????????????????????????????-?-?p--p-?----p?-np--p-nppbpr-bqr-k- |
| dukhq8lu | duck | 10 | 5 | 163 | 0.20 | c8f5 | 290 | 1 | 31 | 9 | 7 | 2/2 | 2 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| dukhq8lu | duck | 12 | 6 | 165 | 0.30 | e7e6 | 519 | 1 | 38 | 6 | 6 | 2/2 | 2 | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| 70i3cc0s | IAmAVirus | 10 | 5 | 157 | 0.30 | d7d6 | 11506 | 1 | 25 | 6 | 6 | 1/1 | 1 | ????????????????????????????P?-?-----?-------np-ppppppbprnbq-rk- |
| y9sa8t4u | Cranberry Lemo | 10 | 5 | 163 | 0.20 | c8f5 | 290 | 1 | 31 | 9 | 7 | 3/3 | 3 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| y9sa8t4u | Cranberry Lemo | 12 | 6 | 165 | 0.30 | e7e6 | 519 | 1 | 38 | 6 | 6 | 3/3 | 3 | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| f8qm6hoi | Cranberry Lemo | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 2/2 | 2 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| yje67p3d | Magnus Monte C | 11 | 6 | 159 | 0.03 | e2e3 | 44 | 1 | 38 | 3 | 3 | - | - | R--QKBNRPP--PPPP--N-------?P-B--?-?p-?-????-???-??-??????-?????? |
| yje67p3d | Magnus Monte C | 13 | 7 | 161 | 0.19 | f1d3 | 240 | 1 | 46 | 4 | 1 | - | - | R--QKBNRPP---PPP--N-P------P-B--?-?p-?---??-???-??-??????-?????? |
| yje67p3d | Magnus Monte C | 15 | 8 | 163 | 0.30 | a1c1 | 751 | 1 | 52 | 1 | 0 | - | - | R--QK-NRPP---PPP--NBP------P-B--?-?p-----??-??--??-????p?-?????? |
| yje67p3d | Magnus Monte C | 17 | 9 | 165 | 0.30 | g1f3 | 2954 | 1 | 51 | 0 | 0 | - | - | --RQK-NRPP---PPP--NBP------P-B--?-?p-----??-??--??-????p?-?????? |
| nb0p6sxv | HYPOTHERMIA | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 3/3 | 3 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| nb0p6sxv | HYPOTHERMIA | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | 2/2 | 2 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| nb0p6sxv | HYPOTHERMIA | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 32 | 6 | 6 | 2/2 | 2 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbq-rk- |
| u3504uhh | HYPOTHERMIA | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | - | - | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| fsrpz4hq | Team 319 | 10 | 5 | 160 | 0.25 | f8g7 | 409 | 1 | 27 | 0 | 0 | - | - | ????????????????????????????-?-?--pP-?------pnp-pp-p-p-prnbqkb-r |
| jk2b9wwa | Farsight | 10 | 5 | 160 | 0.30 | g8f6 | 1469 | 1 | 37 | 1 | 1 | - | - | ????????????????-????????-?P?B?----p------nbp---ppp--pppr-bqk-nr |
| jk2b9wwa | Farsight | 12 | 6 | 162 | 0.30 | e8g8 | 7298 | 1 | 37 | 1 | 1 | - | - | ????????????????-????????-?P-B-?---p-?----nbpn--ppp--pppr-bqk--r |
| dsf3pxks | Ex Republics | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | 1/1 | 1 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| 5voxnm4s | Decent Chess B | 10 | 5 | 160 | 0.30 | g8f6 | 1469 | 1 | 37 | 1 | 1 | 1/1 | 1 | ????????????????-????????-?P?B?----p------nbp---ppp--pppr-bqk-nr |
| 5voxnm4s | Decent Chess B | 12 | 6 | 162 | 0.30 | e8g8 | 7298 | 1 | 37 | 1 | 1 | 1/1 | 1 | ????????????????-????????-?P-B-?---p-?----nbpn--ppp--pppr-bqk--r |
| 3t6vsx3q | Fogbreakers | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | - | - | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| cmgf7d47 | Fogitos | 10 | 5 | 163 | 0.19 | g8e7 | 204 | 1 | 38 | 0 | 0 | - | - | ??????????P?????-??-???-?-??-?-----p?b----p-p---pp---ppprn-qkbnr |
| 3gjixu7t | Knight Vision | 11 | 6 | 159 | 0.12 | f1g2 | 139 | 1 | 40 | 1 | 0 | - | - | R-BQKBNRPPP--P-P--N---P-----P---?p?P-?--???-p??-???????????????? |
| 3gjixu7t | Knight Vision | 13 | 7 | 161 | 0.30 | c1f4 | 876 | 1 | 38 | 0 | 0 | - | - | R-BQK-NRPPP--PBP--N---P---?-P---?p?P-?--???-p??-???????????????? |
| 3gjixu7t | Knight Vision | 15 | 8 | 163 | 0.30 | g1h3 | 2644 | 1 | 44 | 0 | 0 | - | - | R--QK-NRPPP--PBP--N---P---?-PB--?p?P-?--???-p??-??-??????n?????? |
| 3gjixu7t | Knight Vision | 17 | 9 | 165 | 0.30 | e4e5 | 2390 | 1 | 44 | 0 | 0 | - | - | R--QK--RPPP--PBP--N---PN--?-PB-??p?p-?--???-???-??-??????n?????? |
| oxwzf2iz | Decent Chess B | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | 2/2 | 2 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| oxwzf2iz | Decent Chess B | 12 | 6 | 159 | 0.30 | c8d7 | 7178 | 1 | 30 | 0 | 0 | - | - | ???????????????????????-????-?-?-?-p---------np-ppp-ppbprnbq-rk- |
| oxwzf2iz | Decent Chess B | 14 | 7 | 161 | 0.31 | c7c5 | 20921 | 1 | 30 | 0 | 0 | - | - | ???????????????????????-????-?-?-B-p-------?-np-pppbppbprn-q-rk- |
| 0t74zrx0 | duck | 10 | 5 | 157 | 0.30 | d7d6 | 11506 | 1 | 25 | 6 | 6 | 2/2 | 2 | ????????????????????????????P?-?-----?-------np-ppppppbprnbq-rk- |
| 0t74zrx0 | duck | 12 | 6 | 159 | 0.30 | b8d7 | 101426 | 1 | 32 | 5 | 1 | 1/1 | 1 | ???????????????????????-????P?-?-----------p-np-ppp-ppbprnbq-rk- |
| 0t74zrx0 | duck | 14 | 7 | 161 | 0.30 | e7e5 | 200000 | 0 | 27 | 1 | 1 | 1/1 | 1 | ????????????????????????????P?-?-----?-----p-np-pppnppbpr-bq-rk- |
| 0t74zrx0 | duck | 16 | 8 | 162 | 0.30 | f6e8 | 39487 | 0 | 24 | 0 | 0 | - | - | ????????????????????????????P?-?---Pp?-----p?np-pppn-pbpr-bq-rk- |
| z0aig98o | Foggy Fischer | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | 3/3 | 3 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| z0aig98o | Foggy Fischer | 12 | 6 | 159 | 0.30 | f6d5 | 2536 | 1 | 33 | 1 | 1 | - | - | ???????????????????????-????-?-?---P---------np-ppp-ppbprnbq-rk- |
| flr3hh1v | Cranberry Lemo | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 1/2 | 2 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| cpmn8ums | Decent Chess B | 11 | 6 | 159 | 0.28 | b1c3 | 335 | 1 | 39 | 1 | 1 | 1/1 | 1 | RN-QKBNRPP---PPP----P------P-B--?-??-?---??-???-??p????????????? |
| ft59z06p | Decent Chess B | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 4/4 | 4 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| ft59z06p | Decent Chess B | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | 3/3 | 3 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| 927w8ehb | TA Baseline S | 10 | 5 | 157 | 0.30 | d7d6 | 23740 | 1 | 25 | 6 | 6 | - | - | ????????????????????????????P?-?-----?-------np-ppppppbprnbq-rk- |
| 927w8ehb | TA Baseline S | 12 | 6 | 159 | 0.31 | b8c6 | 143462 | 1 | 32 | 5 | 2 | - | - | ???????????????????????-????P?-?-----------p-np-ppp-ppbprnbq-rk- |
| xwrcona1 | Knight Vision | 10 | 5 | 160 | 0.30 | f8g7 | 25097 | 1 | 32 | 1 | 1 | 1/1 | 1 | ???????????????????????-????P?-?----------pp-np-pp--pp-prnbqkb-r |
| xwrcona1 | Knight Vision | 12 | 6 | 162 | 0.30 | e8g8 | 172193 | 1 | 35 | 1 | 1 | 1/1 | 1 | ???????????????????????-????P?-?----------pp-np-pp--ppbprnbqk--r |
| xwrcona1 | Knight Vision | 14 | 7 | 164 | 0.30 | d6e5 | 110907 | 1 | 33 | 0 | 0 | - | - | ???????????????????????-????-?-?----P-----pp-np-pp--ppbprnbq-rk- |
| 6k7tytc6 | Strongly Invis | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | 4/4 | 4 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| vdua6oh7 | Strongly Invis | 10 | 5 | 163 | 0.17 | c8f5 | 290 | 1 | 31 | 9 | 7 | 4/5 | 4 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| vdua6oh7 | Strongly Invis | 12 | 6 | 165 | 0.30 | e7e6 | 519 | 1 | 38 | 6 | 6 | 4/4 | 4 | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| 34t245rc | Sausage | 14 | 7 | 149 | 0.32 | d7d6 | 200000 | 0 | 25 | 1 | 1 | 1/1 | 1 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| 34t245rc | Sausage | 16 | 8 | 151 | 0.30 | a7a6 | 200000 | 0 | 32 | 1 | 1 | 1/1 | 1 | ???????????????????????-????-?-?-----------p-np-ppp-ppbprnbq-rk- |
| haugyjzn | Next | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | 5/5 | 5 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| xw913qgz | Farsight | 11 | 6 | 159 | 0.09 | f1c4 | 9 | 1 | 38 | 4 | 4 | 1/1 | 1 | R-BQKBNRPPP---PP--N--------Pp---?-?-??---??????-???????????????? |
| 2hxo00oz | Farsight | 10 | 5 | 163 | 0.13 | c8f5 | 290 | 1 | 31 | 9 | 7 | 5/6 | 5 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| 2hxo00oz | Farsight | 12 | 6 | 165 | 0.30 | e7e6 | 519 | 1 | 38 | 6 | 6 | 5/5 | 5 | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| c2jc2117 | TA Baseline A | 37 | 19 | 100 | 0.03 | h6h7 | 1 | 1 | 50 | 0 | 0 | - | - | ?-K----RPP---PP---?B-N----Pn----????-p--p------Q??????-p?????q?? |
| 50h61idz | Team 319 | 11 | 6 | 159 | 0.08 | f4g3 | 127 | 1 | 42 | 2 | 0 | - | - | RN-QK--RPPP--PPP---BPN-----P-B--?-??---?-??b??--???????p???????? |
| toqmp7ys | IAmAVirus | 11 | 6 | 159 | 0.04 | e2e3 | 44 | 1 | 38 | 3 | 3 | 2/2 | 1 | R--QKBNRPP--PPPP--N-------?P-B--?-?p-?-????-???-??-??????-?????? |
| toqmp7ys | IAmAVirus | 13 | 7 | 161 | 0.21 | f1d3 | 240 | 1 | 46 | 4 | 1 | 1/2 | 1 | R--QKBNRPP---PPP--N-P------P-B--?-?p-?---??-???-??-??????-?????? |
| l3qqr2x9 | Gravel Road | 10 | 5 | 163 | 0.14 | e8g8 | 340 | 1 | 26 | 0 | 0 | - | - | ????????????????????????????-?-?--pP-?-------np-pp-pppbprnbqk--r |
| 7yrrmn79 | Gravel Road | 10 | 5 | 163 | 0.14 | c8f5 | 290 | 1 | 31 | 9 | 7 | 6/7 | 6 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| wgnkkvkz | Resting Bishop | 10 | 5 | 160 | 0.30 | d7d6 | 32713 | 1 | 25 | 6 | 6 | - | - | ????????????????????????????P?-?-----?-------np-ppppppbprnbq-rk- |
| wgnkkvkz | Resting Bishop | 12 | 6 | 162 | 0.30 | b8c6 | 172350 | 1 | 32 | 5 | 2 | - | - | ???????????????????????-????P?-?-----------p-np-ppp-ppbprnbq-rk- |
| 9kzu5eir | Foggy Fischer | 10 | 5 | 157 | 0.30 | d7d5 | 118034 | 1 | 25 | 7 | 7 | 6/6 | 6 | ????????????????????????????-?-?-----?-------np-ppppppbprnbq-rk- |
| 9kzu5eir | Foggy Fischer | 12 | 6 | 159 | 0.31 | f6d5 | 2536 | 1 | 33 | 1 | 1 | 1/1 | 1 | ???????????????????????-????-?-?---P---------np-ppp-ppbprnbq-rk- |
| i33669ij | Farsight | 10 | 5 | 160 | 0.30 | d7d6 | 32713 | 1 | 25 | 6 | 6 | 1/1 | 1 | ????????????????????????????P?-?-----?-------np-ppppppbprnbq-rk- |
| i33669ij | Farsight | 12 | 6 | 162 | 0.30 | b8c6 | 172350 | 1 | 32 | 5 | 2 | 1/1 | 1 | ???????????????????????-????P?-?-----------p-np-ppp-ppbprnbq-rk- |
| i33669ij | Farsight | 14 | 7 | 164 | 0.31 | e7e5 | 200000 | 0 | 33 | 1 | 1 | - | - | ???????????????????????-?-?PP?-?--?-------np-np-ppp-ppbpr-bq-rk- |
| i33669ij | Farsight | 36 | 18 | 118 | 0.06 | a7a5 | 128 | 0 | 17 | 0 | 0 | - | - | ????????????????-????????-??????---?p--?-p--?-pBp?p?-p-p?????b-k |
| i33669ij | Farsight | 38 | 19 | 120 | 0.04 | a5a4 | 128 | 0 | 9 | 0 | 0 | - | - | ????????????????????????-???????p--?p--??p-??-p???p??p-p??????-k |
| r2zsm9vh | Farsight | 11 | 6 | 159 | 0.07 | f1c4 | 9 | 1 | 38 | 4 | 4 | 2/2 | 2 | R-BQKBNRPPP---PP--N--------Pp---?-?-??---??????-???????????????? |
| ldwyip4h | Cranberry Lemo | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 2/3 | 3 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| ldwyip4h | Cranberry Lemo | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | 1/1 | 1 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| if83zwbh | Lost Signal | 11 | 6 | 159 | 0.30 | b1d2 | 1926 | 1 | 43 | 0 | 0 | - | - | RN-QK--RPPP--PPP---BPN-----P-B--?-??---?-??-??--??p????p???????? |
| d6iwp3pn | Farsight | 11 | 6 | 159 | 0.08 | f1c4 | 9 | 1 | 38 | 4 | 4 | 3/3 | 3 | R-BQKBNRPPP---PP--N--------Pp---?-?-??---??????-???????????????? |
| ekp4au52 | Lost Signal | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 3/4 | 4 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| ekp4au52 | Lost Signal | 12 | 6 | 162 | 0.33 | e8g8 | 103907 | 1 | 34 | 8 | 8 | 2/2 | 2 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| ekp4au52 | Lost Signal | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 32 | 6 | 6 | 1/1 | 1 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbq-rk- |
| ekp4au52 | Lost Signal | 16 | 8 | 165 | 0.31 | a7a5 | 200000 | 0 | 27 | 3 | 3 | - | - | ????????????????????????????-?-?---p-?----p?-np-pp-nppbpr-bq-rk- |
| 2v6mg4ha | Strongly Invis | 10 | 5 | 163 | 0.13 | c8f5 | 290 | 1 | 31 | 9 | 7 | 7/8 | 7 | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| 2v6mg4ha | Strongly Invis | 12 | 6 | 165 | 0.30 | e7e6 | 519 | 1 | 38 | 6 | 6 | 6/6 | 6 | ?-????????-????????-???-?-?P-?-?--?p-b----n-----pp--ppppr--qkbnr |
| n9bu38xz | Decent Chess B | 10 | 5 | 160 | 0.30 | f8g7 | 19053 | 1 | 31 | 11 | 10 | 5/5 | 5 | ???????????????????????-????-?-?---p------p--np-pp--pp-prnbqkb-r |
| n9bu38xz | Decent Chess B | 12 | 6 | 162 | 0.30 | e8g8 | 103907 | 1 | 34 | 8 | 8 | 4/4 | 4 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbqk--r |
| n9bu38xz | Decent Chess B | 14 | 7 | 164 | 0.30 | b8d7 | 200000 | 0 | 32 | 6 | 6 | 3/3 | 3 | ???????????????????????-????-?-?---p------p--np-pp--ppbprnbq-rk- |
| n9bu38xz | Decent Chess B | 16 | 8 | 165 | 0.30 | a7a5 | 200000 | 0 | 27 | 3 | 3 | 2/2 | 2 | ????????????????????????????-?-?---p-?----p?-np-pp-nppbpr-bq-rk- |
| m9ajv66u | Knight Vision | 11 | 6 | 159 | 0.14 | g1h3 | 119 | 1 | 40 | 1 | 0 | - | - | R-BQKBNRPPP--P-P--N---P-----P---?p?P-?--???-p??-???????????????? |
| m9ajv66u | Knight Vision | 13 | 7 | 161 | 0.30 | a2a3 | 215 | 1 | 37 | 0 | 0 | - | - | R-BQKB-RPPP--P-P--N---PN----P--??p?P-?--????p??-???????????????? |
| m9ajv66u | Knight Vision | 15 | 8 | 163 | 0.30 | d5e6 | 1901 | 1 | 38 | 0 | 0 | - | - | R-BQKB-R-PP--P-PP-N---PN----P--??p?P-?--????p??-???????????????? |
| m9ajv66u | Knight Vision | 17 | 9 | 165 | 0.30 | c1g5 | 545 | 1 | 40 | 0 | 0 | - | - | R-BQKB-R-PP--P-PP-N---PN----P--??p?--?--???p???-???????????????? |
| m9ajv66u | Knight Vision | 19 | 10 | 166 | 0.30 | g5e3 | 101 | 1 | 45 | 0 | 0 | - | - | R--QKB-R-PP--P-PP-N---PN----P---?p?--?B-???p?-?p????n??????????? |
| m9ajv66u | Knight Vision | 21 | 11 | 168 | 0.30 | d1h5 | 101 | 1 | 44 | 0 | 0 | - | - | R--QKB-R-PP--P-PP-N-B-PN----P--??pp--?p-???p???????????????????? |
| m9ajv66u | Knight Vision | 23 | 12 | 170 | 0.31 | h3g5 | 73 | 1 | 47 | 0 | 0 | - | - | R---KB-R-PP--P-PP-N-B-PN----P---?pp--?pQ??????-p?????-??????-??? |
| m9ajv66u | Knight Vision | 25 | 13 | 171 | 0.30 | g5f7 | 733 | 1 | 51 | 0 | 0 | - | - | R---KB-R-PP--P-PP-N-B-P-----P---?pp--?NQ????p?-p?????-?-????-??? |
| m9ajv66u | Knight Vision | 27 | 14 | 173 | 0.30 | e4e5 | 759 | 1 | 57 | 0 | 0 | - | - | R---KB-R-PP--P-PP-N-B-P-----P---?pp----Q???p??-p?????N?????-???r |
| m9ajv66u | Knight Vision | 29 | 15 | 175 | 0.30 | f1h3 | 497 | 1 | 54 | 0 | 0 | - | - | R---KB-R-PP--P-PP-N-B-P---------?pp-Pn-Q???p??-p?????N?????-???r |
| m9ajv66u | Knight Vision | 31 | 16 | 176 | 0.30 | f2e3 | 497 | 1 | 47 | 0 | 0 | - | - | R---K--R-PP--P-PP-N?n-PB--??----?p?-P--Q???pp?-p?????N?????-???r |
| m9ajv66u | Knight Vision | 33 | 17 | 178 | 0.30 | e1g1 | 1116 | 1 | 46 | 0 | 0 | - | - | R---K--R-PP----PP-N?P-PB--??-?--?p?-P--Q???pp?-p?????N?????-???- |
| m9ajv66u | Knight Vision | 35 | 18 | 180 | 0.30 | a3a4 | 1116 | 1 | 48 | 0 | 0 | - | - | R----RK--PP?---PP-N?P-PB--??----?p?pP--Q???-p--p?????N?????-???- |
| m9ajv66u | Knight Vision | 37 | 19 | 182 | 0.31 | c3d5 | 628 | 1 | 47 | 0 | 0 | - | - | R----RK--PP?---P--N?P-PBP???------?pP--Q???-p--p?????N?????-???- |
| cmpp8ys6 | Knight Vision | 10 | 5 | 163 | 0.30 | e7e6 | 180 | 1 | 31 | 9 | 1 | - | - | ???????????????????????-?-?P??-?--?p------n-----pp--ppppr-bqkbnr |
| cmpp8ys6 | Knight Vision | 12 | 6 | 165 | 0.30 | f8d6 | 1899 | 1 | 38 | 2 | 1 | - | - | ????????????????-????????-?P???----p------n-p---pp---pppr-bqkbnr |
| cmpp8ys6 | Knight Vision | 14 | 7 | 167 | 0.30 | g8e7 | 8664 | 1 | 44 | 1 | 0 | - | - | ???????????????P-?????-??-?P?-?----p------nbp---pp---pppr-bqk-nr |
| cmpp8ys6 | Knight Vision | 16 | 8 | 168 | 0.30 | e8g8 | 47454 | 1 | 39 | 0 | 0 | - | - | ???????????????P-?????-??-?P?-??---p------nbp---pp--npppr-bqk--r |
| cmpp8ys6 | Knight Vision | 18 | 9 | 170 | 0.30 | c8d7 | 200000 | 0 | 36 | 0 | 0 | - | - | ???????????????P-?????-??-?P?-??---p------nbp---pp--npppr-bq-rk- |
| cmpp8ys6 | Knight Vision | 20 | 10 | 172 | 0.30 | e7g6 | 200000 | 0 | 40 | 0 | 0 | - | - | ???????????????P-?????-??-?P?-??---p------nbp---pp-bnpppr--q-rk- |
| cmpp8ys6 | Knight Vision | 22 | 11 | 173 | 0.31 | a8c8 | 200000 | 0 | 46 | 0 | 0 | - | - | ???????????????P-?????-??-?P?-?----p------nbp-n-pp-b-pppr--q-rk- |
| cmpp8ys6 | Knight Vision | 24 | 12 | 175 | 0.30 | f7f6 | 200000 | 0 | 44 | 0 | 0 | - | - | ???????????????P-?????-??-?P?-?----p------nbp-n-pp-b-ppp--rq-rk- |
| cmpp8ys6 | Knight Vision | 26 | 13 | 177 | 0.32 | g6e7 | 132486 | 0 | 42 | 0 | 0 | - | - | ???????????????--?????-??-?P?-?P---p--?---nbppn-pp-b--pp--rq-rk- |
| cmpp8ys6 | Knight Vision | 28 | 14 | 179 | 0.31 | f8f7 | 200000 | 0 | 38 | 0 | 0 | - | - | ???????????????--?????-??-?P?-??---p------nbpp--pp-bn-pp--rq-rk- |
| cmpp8ys6 | Knight Vision | 30 | 15 | 180 | 0.31 | h7h6 | 200000 | 0 | 37 | 0 | 0 | - | - | ???????????????--?????-??-?P?-??---p---?--nbpp--pp-bnrpp--rq--k- |
| cmpp8ys6 | Knight Vision | 32 | 16 | 182 | 0.31 | e6e5 | 45593 | 0 | 35 | 0 | 0 | - | - | ????????????????-????????-?P?N??---p---?--nbpp-ppp-bnrp---rq--k- |
| cmpp8ys6 | Knight Vision | 34 | 17 | 184 | 0.32 | e5d4 | 17584 | 0 | 37 | 0 | 0 | - | - | ????????????????-????????-?P-?P?---Np--?--nb-p-ppp-bnrp---rq--k- |
| cmpp8ys6 | Knight Vision | 36 | 18 | 185 | 0.32 | c6d4 | 462 | 0 | 40 | 0 | 0 | - | - | ???????????????--?????-??-?B?-P?---N---?--nb-p-ppp-bnrp---rq--k- |
| cmpp8ys6 | Knight Vision | 38 | 19 | 187 | 0.32 | d6e5 | 128 | 0 | 43 | 0 | 0 | - | - | ???????????????--?N???-?P--??-P?---N---?---b-p-ppp-bnrp---rq--k- |
| cmpp8ys6 | Knight Vision | 40 | 20 | 189 | 0.31 | e7d5 | 479 | 0 | 42 | 0 | 0 | - | - | ???????????????-??N???-?P?--?-P?---Nb--?-----p-ppp-bnrp---rq--k- |
| cmpp8ys6 | Knight Vision | 42 | 21 | 190 | 0.31 | d8a5 | 145 | 0 | 42 | 0 | 0 | - | - | ?????????PP????-??-???-?P?--?-P?---?b--?-----p-ppp-b-rp---rq--k- |
| cmpp8ys6 | Knight Vision | 44 | 22 | 192 | 0.31 | d7a4 | 1628 | 0 | 50 | 0 | 0 | - | - | ????-????PP-???-??-???-?P---?-P?q--Nb--?-----p-ppp-b-rp---r---k- |
| cmpp8ys6 | Knight Vision | 46 | 23 | 194 | 0.30 | a4c2 | 567 | 0 | 50 | 0 | 0 | - | - | ????-????PP-???-?--???-?b---?-??q--Nb--?----?p-ppp---rp---r---k- |
| enti5chy | Farsight | 11 | 6 | 159 | 0.06 | f1c4 | 9 | 1 | 38 | 4 | 4 | 4/4 | 4 | R-BQKBNRPPP---PP--N--------Pp---?-?-??---??????-???????????????? |


## 4. The two slowest moves of each game

358 moves (two per game, by think): 327 slow-mode, 31 normal-mode (games whose set never reached 1000 early). Own move
number median 9 (p10 3, p90 15), clock before median 152 s, think 6.16-10.23 s (median 8.95). Set size median 3204
(p10 1073); 325 of 358 have >= 1000 states, 7 are at our cap. Hidden enemy pieces median 14 of 16. Fog check: 0; visible
check: 1; capture played: 45 (12.6%, vs 22% of all moves); view changed after the opponent's move: 67 (19%, vs 54% of all
moves). Material swing since the previous own move: 0 in 333, +-1 in 11, +-2/3 in 14. So the slowest moves are the
top of the budget schedule (high clock, early ply) in the slow mode: opening positions where the opponent's last moves
were invisible and the consistent set has just passed 1000; nothing tactical is special about them.

Top 30 by think:

| game | opp | ply | n | clock | think | ratio | mode | size | exact | hidden | legal | fog check | swing | move |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| xn0i0st0 | ADARSH | 22 | 11 | 170 | 10.23 | 1.50 | slow | 15162 | 0 | 13 | 33 | 0 | +0 | h5f4 |
| xn0i0st0 | ADARSH | 24 | 12 | 162 | 10.01 | 1.50 | slow | 128 | 0 | 11 | 34 | 0 | +3 | f4d3 |
| yje67p3d | Magnus Monte C | 19 | 10 | 166 | 9.86 | 1.50 | slow | 10365 | 1 | 13 | 52 | 0 | +0 | e1g1 |
| ekp4au52 | Lost Signal | 18 | 9 | 167 | 9.82 | 1.50 | slow | 200000 | 0 | 16 | 27 | 0 | +0 | a5a4 |
| r340htvx | Strongly Invis | 18 | 9 | 167 | 9.82 | 1.50 | slow | 43886 | 0 | 14 | 27 | 0 | +0 | c6d5 |
| 2oqyl04l | Strongly Invis | 18 | 9 | 167 | 9.82 | 1.50 | slow | 200000 | 0 | 16 | 27 | 0 | +0 | a5a4 |
| n9bu38xz | Decent Chess B | 18 | 9 | 167 | 9.82 | 1.50 | slow | 200000 | 0 | 16 | 27 | 0 | +0 | a5a4 |
| 0t74zrx0 | duck | 18 | 9 | 164 | 9.70 | 1.50 | slow | 200000 | 0 | 16 | 25 | 0 | +0 | f7f5 |
| yje67p3d | Magnus Monte C | 21 | 11 | 159 | 9.66 | 1.50 | slow | 7021 | 1 | 13 | 47 | 0 | +0 | d3b1 |
| nb0p6sxv | HYPOTHERMIA | 16 | 8 | 165 | 9.63 | 1.50 | slow | 144906 | 0 | 15 | 28 | 0 | +0 | d5e4 |
| xwrcona1 | Knight Vision | 16 | 8 | 165 | 9.62 | 1.50 | slow | 2385 | 1 | 14 | 35 | 0 | +0 | f6d5 |
| uwyl0705 | Cross-Register | 16 | 8 | 165 | 9.62 | 1.50 | slow | 144906 | 0 | 15 | 28 | 0 | +0 | d5e4 |
| i33669ij | Farsight | 16 | 8 | 165 | 9.62 | 1.50 | slow | 101649 | 0 | 14 | 34 | 0 | -1 | c6e5 |
| 2oqyl04l | Strongly Invis | 20 | 10 | 159 | 9.62 | 1.50 | slow | 61666 | 0 | 15 | 30 | 0 | +0 | b7b5 |
| ekp4au52 | Lost Signal | 20 | 10 | 159 | 9.62 | 1.50 | slow | 30629 | 0 | 15 | 29 | 0 | -1 | d7b6 |
| n9bu38xz | Decent Chess B | 20 | 10 | 159 | 9.62 | 1.50 | slow | 200000 | 0 | 16 | 29 | 0 | +0 | b7b5 |
| r340htvx | Strongly Invis | 20 | 10 | 159 | 9.61 | 1.50 | slow | 28792 | 0 | 14 | 26 | 0 | +0 | d7b6 |
| 2v6mg4ha | Strongly Invis | 14 | 7 | 167 | 9.57 | 1.50 | slow | 1643 | 1 | 14 | 46 | 0 | +0 | g8f6 |
| vdua6oh7 | Strongly Invis | 14 | 7 | 167 | 9.56 | 1.50 | slow | 1643 | 1 | 14 | 46 | 0 | +0 | g8f6 |
| wm27pl2o | Team 319 | 14 | 7 | 167 | 9.56 | 1.50 | slow | 1643 | 1 | 14 | 46 | 0 | +0 | g8f6 |
| wtlwy1lc | TUM | 14 | 7 | 167 | 9.56 | 1.50 | slow | 200000 | 0 | 16 | 32 | 0 | +0 | b8d7 |
| dukhq8lu | duck | 14 | 7 | 167 | 9.55 | 1.50 | slow | 1643 | 1 | 14 | 46 | 0 | +0 | g8f6 |
| oxwzf2iz | Decent Chess B | 16 | 8 | 162 | 9.50 | 1.50 | slow | 20211 | 1 | 15 | 35 | 0 | +0 | d8b6 |
| 2q9kqwo1 | Cranberry Lemo | 16 | 8 | 162 | 9.50 | 1.50 | slow | 39487 | 0 | 14 | 27 | 0 | -1 | d7e5 |
| 0t74zrx0 | duck | 20 | 10 | 156 | 9.49 | 1.50 | slow | 12384 | 0 | 15 | 29 | 0 | -1 | g6f5 |
| ldwyip4h | Cranberry Lemo | 14 | 7 | 164 | 9.44 | 1.50 | slow | 57055 | 1 | 15 | 32 | 0 | +0 | b7b6 |
| ft59z06p | Decent Chess B | 14 | 7 | 164 | 9.44 | 1.50 | slow | 13598 | 1 | 15 | 31 | 0 | +0 | f6h5 |
| jk2b9wwa | Farsight | 14 | 7 | 164 | 9.44 | 1.50 | slow | 4924 | 1 | 14 | 34 | 0 | +0 | c6e7 |
| 5voxnm4s | Decent Chess B | 14 | 7 | 164 | 9.43 | 1.50 | slow | 39985 | 1 | 14 | 33 | 0 | +0 | f8e8 |
| wgnkkvkz | Resting Bishop | 14 | 7 | 164 | 9.43 | 1.50 | slow | 20794 | 1 | 13 | 33 | 0 | +0 | e7e5 |


The two highest-ratio moves per game (think / normal budget) are all 1.499-1.504: there is no regime above 1.5x.

## Conclusion: the architecture, and what would falsify it

Most specific statement supported by the data:

1. Greek Gift maintains the complete set of positions consistent with its observations, keyed on board plus castling
   rights (en passant not distinguished), at least up to 1000 positions, exactly as our PositionSet does. Evidence: the
   1.5x budget switches at a count of exactly 1000 with zero exceptions in 309 borderline sets once en passant is
   ignored, and with 27 exceptions all on the same side when it is not. A sampler or a particle filter would not produce
   a sharp threshold at a round number on our exact count.
2. Its time manager is `min(1.5^[set >= 1000] x (2 + (clock - 2)/D(ply)), clock/6)` with D(ply) a fixed table
   (42.5 at ply 1, 16 at ply 90), plus a half budget when a single root move dominates. The budget is decided before the
   search from the clock, the ply and the set-size flag only (residual sd 7-16 ms, uncorrelated with the set size over
   five orders of magnitude, with legal moves or with captures): the search is an anytime procedure that stops at its
   deadline, not a loop with a fixed per-board cost (such a loop would show time growing with the set or a cap that bites
   at large sets).
3. A small opening book keyed on the view, used stochastically, produces the 0.3 s moves at own moves 5-9.
4. Move choice is randomised (earlier report), time is not.

What would falsify it: (a) a slow-mode move with an en-passant-free count below 1000, or a normal move with a count
of 1000+, in a game where our set was never cut (none in 4305 such moves); (b) a 1.5x move whose set we can prove is
below 1000 because the opponent's moves were all visible; (c) think times in the slow mode that grow with the set size
above the cap (they do not: 1.501 at 100000+ vs 1.500 at 1000-3000); (d) a fog-of-war-specific feature (fog check,
captures available) shifting the budget by more than 10 ms (none does); (e) a 0.3 s move at a view never seen in any
game with a non-standard reply, which would make the quick moves a cache hit on the running process rather than a
book (61 of 61 quick moves with a prior identical sequence were quick in the prior game too, but 94 quick moves have no
prior in this data set, so the book is bigger than what these games exercised).

Practical use: we can read Greek Gift's belief size off its clock. A 1.5x think after our move tells us its consistent
set has 1000+ positions, i.e. it has not pinned down our last moves; a 1.0x think tells us it has fewer than 1000
candidates for our position. A 0.3 s move tells us it is in book and did not search at all.
