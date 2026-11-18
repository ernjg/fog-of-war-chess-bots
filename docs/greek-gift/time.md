# Greek Gift (v30): clock usage and determinism

Data: 179 arena games of Greek Gift v30 (180 s + 2 s), 150 arena games of Magnus Monte Carlsen v4.
Scripts: `time_analysis.py` (main tables, raw output in `time_raw.md`), `rule_probe.py`, `rule_probe2.py`, `rule_probe3.py`, `rule_probe4.py` in this folder.
Run with `uv run python -P <script>` (the `-P` keeps the folder's `inspect.py` off `sys.path`).

Clock convention, checked against the data: ply-0 clocks are 180/180; the increment is added after the move, so
think = clock before − clock after + 2. Greek Gift as white at ply 1: 180.00 → 175.81 = 6.19 s. Our v4 at ply 1:
180.00 → 181.97 = 0.03 s. No negative think times under this convention (smallest 0.001 s).

## Summary

- Greek Gift spends about 5.2 s per move on average and burns its clock down to a reserve of 12 s in half of its games
  (90 of 179 end below 20 s; the clock never goes below 12.0 s). It uses ~234 s of thinking per game against
  our v4's ~175 s (v4 ends with 84 s on average).
- Its time rule is deterministic and fully explained by the clock and its own move number:
  `think = 2 + (clock − 12) / D(n)`, with `D(n) ≈ 40.75 − 0.75·n` (floor ≈ 6) in "normal" mode and
  `D(n) ≈ 23.5 − 0.5·n` (floor ≈ 6) in a "slow" mode that is 1.7–2x as long. Median fit error of the normal
  mode is 0.02 s. Below 12 s on the clock it plays on the increment alone (2.00 s per move, for 150+ moves if needed).
- The slow mode is chosen per move and looks belief-driven: it is twice as likely when its view did not change
  after the opponent's move (51–64% vs 26–37%), and rises with the number of hidden enemy pieces (5% at 0–5 hidden,
  59% at 12–13). It is not triggered by captures or by seeing the enemy king.
- There is no startup cost: the first move takes 6.19–6.24 s, exactly what the formula gives at n=1 and 180 s.
- About 2% of moves (155) are played in ~0.30 s. They cluster at its own moves 5–8 (typical replies: e8g8, f8g7,
  b8d7, c8f5, d7d6) and in two late games vs Knight Vision that were almost entirely played at 0.30 s. They are
  more common when the exact observation sequence had already occurred in an earlier game (14% vs 1.3%), but most
  quick moves have no prior in this data set, so it is not simply a cache.
- Move choice is NOT deterministic. At black's move 1, with an identical view in all 89 games, it played c7c6 47 times,
  g8f6 32 times and five other moves 10 times. At white's move 2 after 1.d4 with nothing seen: c2c4 23, c1f4 21,
  b1c3 31 (split across two observation keys). Over plies 1–12, 119 observation sequences recur; only 93 (78%)
  always get the same reply, and 26% of game pairs sharing a sequence get different replies. The think time, by
  contrast, is identical to 0.01 s across games with the same sequence.
- It beats fast and slow opponents alike: 14-0 against the five opponents that average under 3 s per move,
  149-11-5 against the rest. All 5 losses and 5 draws came against opponents that think 3.5–5 s per move; 9 of
  those 10 games ended with Greek Gift at or near its 12 s reserve. All 5 draws were threefold repetitions.

## 1. Think time per move

Think time by ply bucket (s)

| ply | Greek Gift n | mean | median | p90 | max | GG opponents mean | median | max | MMC v4 mean | median | max | our opponents mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-10 | 895 | 6.10 | 6.17 | 6.23 | 9.27 | 5.02 | 5.01 | 15.06 | 5.03 | 7.00 | 7.68 | 4.05 |
| 11-20 | 895 | 6.58 | 6.07 | 9.09 | 9.86 | 5.63 | 5.70 | 11.86 | 5.73 | 6.56 | 7.71 | 5.26 |
| 21-40 | 1777 | 6.76 | 6.92 | 8.53 | 10.23 | 5.19 | 5.26 | 11.40 | 5.04 | 5.63 | 7.69 | 4.83 |
| 41-60 | 1543 | 5.68 | 5.41 | 7.22 | 8.80 | 4.14 | 4.21 | 10.96 | 4.42 | 4.75 | 7.14 | 3.79 |
| 61+ | 3000 | 3.24 | 2.99 | 5.03 | 7.12 | 2.95 | 3.02 | 8.50 | 3.25 | 3.51 | 5.92 | 2.84 |
| all | 8110 | 5.16 | 5.48 | 8.17 | 10.23 | 4.18 | 3.88 | 15.06 | 4.46 | 4.74 | 7.71 | 3.97 |

Minimum think: Greek Gift 0.03 s; its opponents 0.00 s; v4 0.01 s. Greek Gift never exceeded 10.3 s on a move.

Histogram of Greek Gift think (all 8110 moves): <0.5 s: 155; 0.5-1: 0; 1-2: 98; 2-3: 1411; 3-4: 766; 4-5: 978;
5-7: 3187; 7-10: 1513; 10-15: 2. (v4: <0.5: 132; 0.5-1: 105; 1-2: 599; 2-3: 407; 3-4: 826; 4-5: 1165; 5-7: 2090; 7-10: 534.)

Clock remaining at the end of the game (s)

| who | games | mean | median | min | max | games ending < 20 s | < 60 s |
|---|---|---|---|---|---|---|---|
| Greek Gift | 179 | 36.8 | 19.7 | 12.0 | 195.4 | 90 | 138 |
| GG opponents | 179 | 80.2 | 68.9 | 8.2 | 320.4 | 14 | 75 |
| MMC v4 | 150 | 83.8 | 81.2 | 18.9 | 177.8 | 1 | 36 |

- Greek Gift is below 20 s after 1713 of its moves, in 90 of 179 games; below 60 s in 138 games. Lowest clock
  ever: 12.0 s (game 2kb5hu9d, ply 235, vs Strongly Invisible, 326 plies). Opponents go below 20 s in 17 games; v4 in 1 of 150.
- Game length (GG games): mean 91 plies, median 86, max 326; Greek Gift makes 45 moves per game on average.
- Total think per game: Greek Gift mean 234 s (median 245, max 494); net clock change −143 s per game.

### Shape of the rule

Think is not a constant and not a fixed fraction of the remaining clock. think/remaining has median 0.077 but ranges
from 0.037 (p10) to 0.167 (p90); a constant model leaves residual sd 2.14 s and a fixed-fraction model 3.33 s.
Pearson r(think, remaining) = 0.64. The dependence on the clock is through a "moves to go" divisor that falls with
Greek Gift's own move number n, plus a 12 s reserve and the increment:

    think = 2 + max(clock − 12, 0) / D(n)

Measured D(n) = (clock − 12) / (think − 2), median over games (the spread across games at a given n is ±0.1):

| GG move n | 1 | 2 | 3 | 4 | 6 | 8 | 10 | 15 | 20 | 25 | 30 | 35 | 40 | 45 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D normal mode | 40.0 | 39.2 | 38.5 | 37.7 | 36.2 | 34.8 | 33.4 | 29.7 | 26.0 | 22.3 | 18.7 | 15.6 | 11.0 | 7.9 |
| D slow mode | – | – | – | 21.5 | 20.6 | 19.7 | 18.9 | 16.4 | 13.8 | 11.2 | 8.4 | 6.0 | – | – |

Normal mode: D(n) ≈ 40.75 − 0.75·n, floored near 6 (4403 moves, median absolute fit error 0.024 s). Slow mode:
D(n) ≈ 23.5 − 0.5·n, floored near 6; relative to the normal budget it spends 1.72x the excess over the increment at
n<15, rising to ~2x at n=25–35. The ratio (think − 2)/(normal prediction − 2) is bimodal: 53% of moves at 0.85–1.15,
34% at 1.3+ (mostly 1.7–1.9), the rest at 0.6–0.85 (late moves, n 35–50, where the floor of D bites) or quick moves.
Once the clock reaches 12 s it plays at exactly 2.00 s per move (game 2kb5hu9d: 150 consecutive moves at 2.00–2.02 s).

Think by remaining clock (excluding each game's first move)

| clock before move | n | GG mean | median | p10 | p90 | median think/clock | v4 n | v4 mean | v4 median | v4 rule (bucket midpoint) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-30 | 2167 | 2.66 | 2.37 | 2.00 | 3.63 | 0.166 | 58 | 2.29 | 2.33 | 2.10 |
| 30-60 | 1217 | 4.97 | 4.75 | 3.77 | 6.25 | 0.113 | 564 | 2.90 | 3.10 | 3.10 |
| 60-90 | 1166 | 5.82 | 5.18 | 4.64 | 7.29 | 0.074 | 1100 | 3.61 | 3.97 | 4.10 |
| 90-120 | 1084 | 6.64 | 5.76 | 5.26 | 8.18 | 0.059 | 1407 | 4.43 | 4.93 | 5.10 |
| 120-150 | 1010 | 7.17 | 6.08 | 5.73 | 8.86 | 0.047 | 1261 | 5.19 | 5.88 | 6.10 |
| 150-170 | 906 | 5.98 | 6.10 | 0.30 | 9.20 | 0.038 | 785 | 5.65 | 6.73 | 6.93 |
| 170-200 | 381 | 5.96 | 6.17 | 6.14 | 6.21 | 0.035 | 533 | 4.79 | 7.04 | 7.60 |

Our v4 rule min(clock/30 + 1.6, clock/5) gives 7.6 s at 180 s, 3.6 s at 60 s, 2.3 s at 20 s; the observed v4
medians track it (r(think, clock) = 0.39, median think/clock 0.045). Greek Gift spends more than v4 at every clock
level below 150 s (at 30–60 s: 5.0 s vs 2.9 s; at 60–90 s: 5.8 vs 3.6) and reaches its reserve where v4 stays above 60 s.

Other observables (excluding first move):

| split | n | mean | median | p90 |
|---|---|---|---|---|
| pieces on board 2-9 | 313 | 2.49 | 2.18 | 3.49 |
| pieces 10-15 | 1468 | 3.19 | 3.00 | 4.69 |
| pieces 16-21 | 2006 | 4.40 | 4.65 | 6.36 |
| pieces 22-25 | 1224 | 5.69 | 5.64 | 7.59 |
| pieces 26-29 | 1297 | 6.79 | 6.58 | 8.56 |
| pieces 30-32 | 1623 | 6.58 | 6.17 | 9.07 |
| view changed since last own move: yes | 3872 | 5.19 | 5.41 | 7.69 |
| view changed: no | 4059 | 5.09 | 5.44 | 8.54 |
| as white | 3759 | 5.14 | 5.53 | 7.81 |
| as black | 4172 | 5.14 | 5.29 | 8.45 |
| in games it won | 7127 | 5.16 | 5.45 | 8.19 |
| in games it lost/drew | 804 | 4.96 | 5.15 | 8.23 |

The piece-count gradient is explained by the clock and move number (fewer pieces = later = less clock and lower D);
within a clock band the piece count still adds something because the slow mode is more frequent with more pieces
(at clock 90–120: median 5.5 s with 16–23 pieces vs 7.7 s with 24–32).

## 2. First move and belief-size proxies

| move | n | mean | median | min | max |
|---|---|---|---|---|---|
| GG move 1 (as white) | 90 | 6.19 | 6.19 | 6.19 | 6.20 |
| GG move 1 (as black) | 89 | 6.23 | 6.23 | 6.22 | 6.24 |
| GG move 2 | 179 | 6.19 | 6.17 | 6.16 | 6.21 |
| GG moves 3+ | 7752 | 5.11 | 5.36 | 0.03 | 10.23 |
| opponents' move 1 | 179 | 4.83 | 5.07 | 0.00 | 15.06 |
| MMC v4 move 1 | 150 | 4.28 | 4.28 | 0.03 | 7.55 |

No startup cost: move 1 is exactly the formula value (2 + 168/40 = 6.2 s) and every game is within 0.05 s of it.
The whole first-move histogram sits in [6, 7). The 0.04 s difference between white and black is consistent with a
fixed per-move overhead of ~0.2 s already included in the 6.19.

Think by Greek Gift's own move number (shows the slow mode appearing from move 4 and peaking at moves 8–12)

| GG move # | n | mean | median | p10 | p90 | max |
|---|---|---|---|---|---|---|
| 1 | 179 | 6.21 | 6.20 | 6.19 | 6.23 | 6.24 |
| 2 | 179 | 6.19 | 6.17 | 6.17 | 6.21 | 6.21 |
| 3 | 179 | 6.40 | 6.15 | 6.14 | 6.18 | 9.27 |
| 4 | 179 | 6.82 | 6.12 | 6.12 | 9.23 | 9.24 |
| 5 | 179 | 4.90 | 6.09 | 0.30 | 6.13 | 9.19 |
| 6 | 179 | 5.30 | 6.07 | 0.30 | 9.14 | 9.26 |
| 7 | 179 | 6.39 | 6.04 | 0.32 | 9.09 | 9.57 |
| 8 | 179 | 6.80 | 6.06 | 5.91 | 9.11 | 9.63 |
| 9 | 179 | 7.11 | 6.19 | 5.88 | 9.07 | 9.82 |
| 10 | 179 | 7.28 | 8.23 | 5.85 | 8.93 | 9.86 |
| 11 | 179 | 7.22 | 8.06 | 5.74 | 8.83 | 10.23 |
| 12 | 179 | 7.20 | 7.91 | 5.69 | 8.78 | 10.01 |
| 15 | 179 | 7.00 | 7.61 | 5.46 | 8.55 | 9.36 |
| 20 | 171 | 6.28 | 5.69 | 4.91 | 7.90 | 9.02 |
| 30 | 139 | 5.14 | 5.02 | 4.04 | 6.35 | 7.59 |

Correlation of think with belief proxies (excluding first move, n = 7931):

| variable | Pearson r | Spearman rho | within-bucket Spearman (ply 1-10 / 11-20 / 21-40 / 41-60 / 61+) |
|---|---|---|---|
| hidden enemy pieces | 0.60 | 0.67 | 0.51 / 0.12 / 0.49 / 0.40 / 0.19 |
| unseen squares | −0.46 | −0.42 | 0.57 / 0.10 / 0.15 / 0.04 / −0.26 |
| pieces on board | 0.65 | 0.70 | |
| remaining clock | 0.65 | 0.73 | |
| ply | −0.69 | −0.75 | |

The raw correlations are dominated by the clock schedule (later = less time, and later = fewer hidden pieces, more
unseen squares). The cleaner test is which mode it picks. Among its moves 3–30 with clock > 20 s (4597 moves, 45% slow):

| view changed after opponent's move | enemy pieces visible | n | P(slow mode) |
|---|---|---|---|
| yes | 0 | 156 | 0.26 |
| yes | 1 | 632 | 0.29 |
| yes | 2 | 801 | 0.37 |
| yes | 3+ | 954 | 0.35 |
| no | 0 | 339 | 0.51 |
| no | 1 | 627 | 0.54 |
| no | 2 | 599 | 0.64 |
| no | 3+ | 489 | 0.64 |

| hidden enemy pieces | n | P(slow) | | unseen squares | n | P(slow) |
|---|---|---|---|---|---|---|
| 0-5 | 110 | 0.05 | | 0-19 | 239 | 0.25 |
| 6-8 | 952 | 0.31 | | 20-24 | 1383 | 0.42 |
| 9-11 | 1570 | 0.52 | | 25-29 | 2076 | 0.49 |
| 12-13 | 978 | 0.59 | | 30-34 | 790 | 0.47 |
| 14-16 | 987 | 0.37 | | 35-44 | 108 | 0.25 |

Slow mode is sticky (63% of slow moves are followed by another slow move; 11% of normal moves by a slow one), is
less likely right after a capture by either side (P = 0.16 after its own capture vs 0.25; 0.11 after losing a piece
vs 0.26) and never depends on seeing the enemy king (never visible before a move in this data, for either mode).
The pattern (unchanged view, many hidden pieces, more pieces on board, mid-opening) is what a belief-size trigger would
produce: when the opponent's move was invisible the set of consistent boards grows and it buys more time.

The 15 longest thinks are all 9.6–10.2 s at its moves 8–13 with 154–170 s on the clock and 29–32 pieces, i.e. the
slow mode at the top of the schedule, not outliers.

Quick moves (155 moves under 1 s, 126 of them at 0.30–0.32 s): by move number 5: 45, 6: 44, 7: 20, 8: 12, then a
tail to move 23. Typical moves e8g8 (15), f8g7 (14), b8d7 (9), c8f5 (9), e7e6, d7d6, d7d5 (8 each). 40 of the 155 are
in games vs Knight Vision; two games on 2026-11-18 16:16 (cmpp8ys6, 19 quick moves of 23; m9ajv66u, 14 of 19) were
played almost entirely at 0.30 s and both were won. Only 14 quick moves are captures. Moves whose full observation
sequence had already occurred in an earlier game are quick 14.3% of the time vs 1.3% otherwise, but 95 of the 155
quick moves have no prior in these 179 games (earlier Greek Gift versions' games are not in the data set).

## 3. Determinism

Key = colour + for every earlier own move (view before it, the move, view after it) + the view before the current move,
restricted to plies 1–12. Two games with the same key gave the bot exactly the same information.

| ply | distinct sequences | repeated (>=2 games) | games in repeats | repeats with one reply | repeats with >1 reply |
|---|---|---|---|---|---|
| 1 | 1 | 1 | 90 | 1 | 0 |
| 2 | 1 | 1 | 89 | 0 | 1 |
| 3 | 3 | 3 | 90 | 1 | 2 |
| 4 | 9 | 8 | 88 | 5 | 3 |
| 5 | 12 | 8 | 86 | 5 | 3 |
| 6 | 27 | 16 | 78 | 10 | 6 |
| 7 | 35 | 16 | 71 | 14 | 2 |
| 8 | 43 | 15 | 61 | 13 | 2 |
| 9 | 56 | 13 | 47 | 9 | 4 |
| 10 | 55 | 15 | 49 | 15 | 0 |
| 11 | 69 | 9 | 30 | 6 | 3 |
| 12 | 64 | 14 | 39 | 14 | 0 |

Total: 119 repeated observation sequences at plies 1–12, 93 (78%) with an identical reply, 26 with two or more
different replies. Pairwise: 12,459 game pairs share a sequence, 9,240 (74%) got the same reply. With a looser key
(colour + ply + current view only) 83 of 117 repeated keys (71%) have a single reply.

Examples of different replies to the same observation:

| ply | colour | replies (count) |
|---|---|---|
| 1 | white | d2d4 (90) — the only fully deterministic choice |
| 2 | black | c7c6 47, g8f6 32, c7c5 3, e7e6 2, g7g6 2, b8c6 2, d7d5 1 (identical view in all 89 games) |
| 3 | white | b1c3 31, e2e4 1, c2c4 1 (one key); c2c4 23, c1f4 21 (another key) |
| 4 | black | g7g6 21, c7c5 2, e7e6 2 |
| 5 | white | e2e3 14, c2c4 2, g1f3 1; c4d5 22, b1c3 1 |
| 6 | black | g7g6 9, g8f6 5; c6d5 9, c8d7 1; b8c6 4, f8g7 2, c7c6 2, d7d5 1, c7c5 1 |
| 7 | white | g1f3 5, f1d3 5, c2c4 1 |
| 9 | white | e2e3 9, b1c3 2 |

Black's first move in chronological order (C = c7c6, N = g8f6, others as letters) shows no drift over the 36 hours,
so this is per-game randomness, not a version change:
`CCCCN5CNNNCNCCECCCCNNCCCCCCNCNBN5CNCBGNCDCNN5NCNNCCCCCGCCNNNNNCCNNCCNNCCNCCNNNNCCNCCECCCC`.

The time budget, by contrast, is deterministic: in every repeated sequence with >=3 games the think times agree to
0.01 s (e.g. 90 games at ply 1: 6.19–6.20 s; one ply-6 sequence of 11 games all at 9.26–9.27 s, i.e. the slow mode
is chosen identically given the same observations). Conclusion: a deterministic time manager and a search with a
random element (randomised opening choice and, given the ply-6/7/9 splits, probably sampled beliefs or a stochastic
search), so replaying a line against it does not reproduce its moves.

## 4. Opponents

| opponent | games | GG W-L-D | opp mean think | opp median | opp max | opp end clock | GG mean think | GG end clock |
|---|---|---|---|---|---|---|---|---|
| Strongly Invisible | 14 | 11-1-2 | 3.87 | 3.69 | 11.40 | 74.8 | 4.81 | 22.5 |
| Cranberry Lemon | 12 | 11-1-0 | 4.84 | 4.34 | 8.05 | 21.3 | 4.85 | 22.3 |
| Farsight | 11 | 10-1-0 | 3.79 | 4.14 | 7.44 | 110.2 | 5.43 | 47.9 |
| Decent Chess Bot | 10 | 9-1-0 | 4.69 | 3.83 | 10.00 | 37.7 | 5.02 | 21.4 |
| Crimson Fog | 10 | 8-2-0 | 3.50 | 3.64 | 4.22 | 118.5 | 5.57 | 35.1 |
| IAmAVirus | 10 | 10-0-0 | 5.49 | 5.25 | 10.59 | 39.0 | 5.64 | 34.9 |
| TA Baseline S | 8 | 8-0-0 | 4.29 | 4.31 | 5.93 | 85.9 | 5.45 | 40.1 |
| Gravel Road | 8 | 7-1-0 | 4.90 | 2.85 | 15.06 | 21.1 | 4.79 | 28.2 |
| Team 319 | 8 | 8-0-0 | 4.66 | 4.82 | 8.93 | 64.0 | 5.33 | 36.5 |
| HYPOTHERMIA | 8 | 6-1-1 | 4.51 | 4.41 | 7.55 | 55.5 | 5.09 | 28.0 |
| duck | 8 | 6-2-0 | 4.57 | 4.33 | 10.36 | 44.0 | 5.14 | 14.5 |
| Knight Vision | 6 | 6-0-0 | 4.60 | 5.24 | 7.23 | 98.9 | 4.98 | 88.6 |
| Lost Signal | 6 | 6-0-0 | 4.53 | 4.16 | 10.95 | 56.2 | 5.05 | 31.8 |
| Foggy Fischer | 6 | 5-1-0 | 4.00 | 3.88 | 7.74 | 86.9 | 5.24 | 30.5 |
| Resting Bishop Faces | 6 | 6-0-0 | 1.99 | 2.46 | 2.60 | 180.6 | 4.95 | 39.6 |
| Instructors | 6 | 6-0-0 | 4.03 | 4.03 | 9.82 | 94.7 | 5.47 | 36.2 |
| Magnus Monte Carlsen | 6 | 6-0-0 | 4.47 | 4.52 | 7.55 | 66.4 | 4.89 | 48.3 |
| Cross-Registered Players | 4 | 4-0-0 | 4.44 | 4.11 | 7.67 | 48.7 | 4.69 | 36.9 |
| Mist Opportunities | 4 | 4-0-0 | 4.78 | 4.87 | 8.22 | 82.0 | 5.57 | 56.0 |
| Next | 4 | 3-0-1 | 4.18 | 2.78 | 10.59 | 38.6 | 4.55 | 14.6 |
| RATIRL | 4 | 3-0-1 | 3.07 | 3.00 | 6.10 | 151.2 | 6.33 | 65.1 |
| In Pawn Sight | 2 | 2-0-0 | 5.46 | 5.38 | 10.61 | 76.1 | 6.09 | 59.4 |
| TA Baseline A | 2 | 2-0-0 | 4.58 | 4.66 | 5.37 | 123.2 | 6.53 | 82.7 |
| Sausage | 2 | 2-0-0 | 1.84 | 1.84 | 1.89 | 184.3 | 6.50 | 60.7 |
| Unicorns | 2 | 2-0-0 | 5.32 | 5.17 | 7.57 | 73.9 | 6.52 | 37.6 |
| TA Baseline P | 2 | 2-0-0 | 0.00 | 0.00 | 0.01 | 241.9 | 6.18 | 52.5 |
| Fogitos | 2 | 2-0-0 | 3.51 | 3.47 | 4.86 | 116.6 | 5.18 | 48.0 |
| Fogbreakers | 2 | 2-0-0 | 0.28 | 0.27 | 1.03 | 267.6 | 4.43 | 57.1 |
| Ex Republics | 2 | 2-0-0 | 4.61 | 4.85 | 7.32 | 82.1 | 5.70 | 43.0 |
| ADARSH | 2 | 2-0-0 | 0.10 | 0.09 | 0.22 | 257.1 | 5.14 | 54.4 |
| TUM | 2 | 2-0-0 | 4.83 | 4.35 | 10.79 | 46.8 | 5.25 | 29.0 |

- Opponents averaging < 1 s per move (3): Greek Gift 6-0-0. 1–3 s (2): 8-0-0. >= 3 s (26): 149-11-5 (91.8%).
  Fast bots are the weak ones here; the opponents that scored against it are the ones that use their clock.
- Six games vs Magnus Monte Carlsen v4 are in the set: 0-6. In those v4 averaged 4.5 s per move, Greek Gift 4.9 s,
  and v4 ended with 66 s on the clock to Greek Gift's 48 s.

Greek Gift's 16 non-wins (174 of 179 games ended by king capture, 5 by threefold repetition):

| game | GG colour | opponent | result | reason | plies | GG end clock | opp end clock | GG mean think |
|---|---|---|---|---|---|---|---|---|
| 2v6mg4ha | black | Strongly Invisible | draw | threefold | 154 | 12.0 | 50.6 | 4.18 |
| zwkhppqp | white | Strongly Invisible | loss | king capturable | 109 | 12.7 | 63.9 | 5.04 |
| i33669ij | black | Farsight | loss | king capturable | 38 | 121.9 | 147.5 | 5.06 |
| hk5xnaw6 | black | Crimson Fog | loss | king capturable | 70 | 33.9 | 124.1 | 6.17 |
| 9kzu5eir | black | Foggy Fischer | loss | king capturable | 134 | 12.4 | 68.2 | 4.50 |
| 7yrrmn79 | black | Gravel Road | loss | king capturable | 126 | 12.9 | 20.0 | 4.65 |
| huj29uxm | white | Decent Chess Bot | loss | king capturable | 83 | 28.5 | 39.9 | 5.61 |
| amxeg49b | white | Crimson Fog | loss | king capturable | 105 | 13.4 | 107.7 | 5.14 |
| wzc5xwqj | black | duck | loss | king capturable | 114 | 12.5 | 49.5 | 4.94 |
| u3504uhh | black | HYPOTHERMIA | draw | threefold | 113 | 12.6 | 41.2 | 4.99 |
| ir53fzsx | black | HYPOTHERMIA | loss | king capturable | 48 | 68.5 | 91.1 | 6.65 |
| f8qm6hoi | black | Cranberry Lemon | loss | king capturable | 136 | 12.1 | 12.0 | 4.47 |
| ww2ykpkn | white | duck | loss | king capturable | 81 | 15.3 | 46.7 | 6.02 |
| ae2yfkb5 | white | Next | draw | threefold | 175 | 12.0 | 16.0 | 3.91 |
| pm3e1zaq | black | RATIRL | draw | threefold | 63 | 34.8 | 130.9 | 6.68 |
| r340htvx | black | Strongly Invisible | draw | threefold | 88 | 14.4 | 85.1 | 5.76 |

By the result field the record is 163 wins, 11 losses, 5 draws (the brief's 163-5-11 is W-D-L). 11 of the 16 non-wins ended with Greek Gift on 12–15 s, i.e. playing on the increment; its
losses are concentrated in long games (median 105 plies vs 86 overall) where it had spent its clock. In short games
it loses only when it is simply outplayed (i33669ij at 38 plies with 122 s left).
