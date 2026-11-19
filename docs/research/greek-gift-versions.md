# Greek Gift across its arena versions: what changed at each jump

Data: the full arena game list (17,314 games, `gg_all_games.json`) for scores and pools; replays of a random 120 games
per version for v1, v2, v14, v16, v21, v25 (public API, cached in `replays/`) and all 179 cached v30 games, replayed
with `starter/referee.py` `FowBoard`; views are the frames' own strings. Scripts here: `fetch.py`, `analyze.py`
(writes `results.pkl`, `raw.md`), `table.py`. Every game is 180+2; think = clock before - clock after + 2.

Definitions. Unseen capture: the victim's pre-move view showed `?` on the capturer's square. Quiet move en prise to an
unseen piece: a non-capture, non-king move landing on a square attacked (true board) by an enemy piece the mover's
pre-move view did not show, undefended or attacker cheaper. Leaving a piece hanging: after the move another own
non-king piece is undefended and attacked by an unseen piece. King rows: any move that leaves the king attacked ends
the game at once, so "king onto an attacked square" and "walk-ins" are exactly the losses by king move and the
`walked_in` losses (kills.md definitions); there is no non-fatal version. "King reachable from an unseen square"
counts, after each own move, unseen squares from which a queen or knight could hit the king over empty squares.
Common-opponent score: this version against the opponents it shares with v25, each weighted by min(games here, games
for v25), next to v25 on the same weights. Balance = P1 N3 B3 R5 Q9, Greek Gift minus opponent.

## Table

| metric | v1 | v2 | v14 | v16 | v21 | v25 | v30 |
|---|---|---|---|---|---|---|---|
| **Arena (all games)** games | 524 | 2010 | 896 | 4232 | 1466 | 7092 | 314 |
| score (all) | 0.580 | 0.659 | 0.768 | 0.737 | 0.829 | 0.889 | 0.893 |
| vs staff bots: games / score | 444 / 0.62 | 1306 / 0.69 | 504 / 0.81 | 1806 / 0.82 | 488 / 0.86 | 1650 / 0.88 | 50 / 0.87 |
| vs non-staff: games / score | 80 / 0.338 | 704 / 0.592 | 392 / 0.712 | 2426 / 0.678 | 978 / 0.814 | 5442 / 0.891 | 264 / 0.898 |
| common-opp score vs v25's score on same opps (n opps) | 0.563 vs 0.916 (7) | 0.646 vs 0.870 (9) | 0.768 vs 0.863 (10) | 0.725 vs 0.863 (13) | 0.829 vs 0.873 (16) | 0.889 vs 0.889 (34) | 0.895 vs 0.913 (28) |
| share of games vs opps v25 also met | 98% | 100% | 100% | 100% | 100% | 100% | 84% |
| draw share (all) / loss reasons (all) | 4.6% / king 208 | 5.8% / king 628 | 4.5% / king 188 | 6.4% / king 979 | 7.2% / king 198 | 4.4% / king 630 | 4.1% / king 27 |
| draw reasons (all) | 3fold 23, 50-move rule 1 | 3fold 112, 50-move rule 4 | 3fold 37, 50-move rule 3 | 3fold 261, 50-move rule 8 | 3fold 101, 50-move rule 4 | 3fold 283, 50-move rule 29 | 3fold 13 |
| game length mean (all) | 78 | 86 | 89 | 94 | 93 | 95 | 92 |
| **Sample** games (W-D-L) | 120 (69-3-48) | 120 (84-7-29) | 120 (89-5-26) | 120 (81-8-31) | 120 (94-7-19) | 120 (109-5-6) | 179 (163-5-11) |
| own moves in sample | 4522 | 5114 | 5253 | 5750 | 5127 | 5365 | 8110 |
| **Time** think mean plies 1-10 / 11-20 / 21-40 / 41-60 / 61+ (s) | 5.5 / 5.6 / 4.7 / 4.3 / 3.3 | 5.1 / 5.7 / 5.4 / 5.1 / 3.9 | 6.4 / 7.2 / 6.5 / 5.5 / 3.3 | 6.4 / 7.0 / 6.5 / 5.4 / 3.3 | 6.5 / 7.2 / 6.6 / 5.5 / 3.3 | 6.6 / 7.4 / 6.6 / 5.6 / 3.2 | 6.1 / 6.6 / 6.8 / 5.7 / 3.2 |
| think mean all / max (s) | 4.44 / 10.5 | 4.82 / 7.3 | 5.22 / 9.2 | 5.04 / 9.3 | 5.33 / 9.3 | 5.27 / 9.3 | 5.16 / 10.2 |
| moves under 0.4 s | 0.1% | 0.1% | 0.1% | 0.0% | 0.0% | 0.0% | 1.9% |
| games opening with a <0.4 s move / book length mean, max (own moves) | 0% / 0.0, 0 | 0% / 0.0, 0 | 0% / 0.0, 0 | 0% / 0.0, 0 | 0% / 0.0, 0 | 0% / 0.0, 0 | 0% / 0.0, 0 |
| clock at ply 40 / 80 / end, mean (s) | 117 / 75 / 88 | 112 / 50 / 60 | 87 / 26 / 39 | 88 / 27 / 34 | 85 / 24 / 38 | 83 / 23 / 34 | 88 / 24 / 37 |
| games ending under 20 s / clock min (s) | 1% / 10.4 | 16% / 12.0 | 38% / 12.0 | 50% / 12.0 | 44% / 12.0 | 45% / 12.0 | 50% / 12.0 |
| fit think = a + (clock-r)/max(f, D-s*n): a, r, D, s, f (median err) | a=2.5 r=45 D=47 s=0 f=4 (0.40) | a=2 r=15 D=60 s=1 f=15 (0.05) | a=2.5 r=12 D=46 s=0.75 f=15 (0.04) | a=2.5 r=12 D=46 s=0.75 f=15 (0.04) | a=2.5 r=12 D=46 s=0.75 f=15 (0.04) | a=2.5 r=12 D=46 s=0.75 f=15 (0.05) | a=2.5 r=12 D=46 s=0.75 f=15 (0.05) |
| think by clock bucket >120 / 60-120 / 30-60 / <30 s (mean s) | 5.2 / 3.9 / 2.8 / 2.8 | 5.4 / 5.0 / 4.1 / 2.7 | 6.8 / 6.0 / 4.8 / 2.6 | 6.7 / 5.9 / 4.8 / 2.6 | 6.8 / 6.1 / 4.8 / 2.7 | 7.0 / 6.2 / 4.9 / 2.7 | 6.5 / 6.2 / 5.0 / 2.7 |
| opponents' think mean (s) | 3.3 | 3.3 | 3.8 | 4.1 | 4.4 | 4.2 | 4.2 |
| **Openings** 1.d4 share as white (n) | 0% (59) | 97% (60) | 100% (53) | 100% (56) | 100% (67) | 100% (51) | 100% (90) |
| first move as white | e2e4 59 | d2d4 58, e2e4 2 | d2d4 53 | d2d4 56 | d2d4 67 | d2d4 51 | d2d4 90 |
| first 3 as white (top 3) | e2e4 g1f3 b1c3 12; e2e4 d2d4 b1c3 10; e2e4 g1f3 c2c4 3 | d2d4 c1f4 e2e3 15; d2d4 d4d5 b1c3 11; d2d4 e2e4 b1c3 8 | d2d4 c1f4 e2e3 13; d2d4 d4d5 b1c3 8; d2d4 e2e4 e4e5 6 | d2d4 c1f4 e2e3 13; d2d4 e2e4 b1c3 12; d2d4 d4d5 b1c3 12 | d2d4 c2c4 c4d5 17; d2d4 d4d5 b1c3 10; d2d4 c1f4 e2e3 9 | d2d4 c2c4 c4d5 15; d2d4 d4d5 b1c3 8; d2d4 b1c3 e2e4 7 | d2d4 c2c4 c4d5 22; d2d4 b1c3 e2e4 19; d2d4 c1f4 e2e3 16 |
| first move as black (n) | d7d5 36, g7g6 17, c7c6 3 (61) | d7d5 60 (60) | d7d5 44, c7c5 15, c7c6 6 (67) | d7d5 41, c7c5 20, c7c6 2 (64) | c7c6 25, g8f6 21, c7c5 3 (53) | c7c6 43, g8f6 18, b8c6 2 (69) | c7c6 47, g8f6 32, c7c5 3 (89) |
| first 3 as black (top 3) | d7d5 c7c6 g8f6 10; d7d5 e7e6 b8d7 5; d7d5 c7c6 c8d7 4 | d7d5 c7c6 g8f6 11; d7d5 c8d7 e7e6 10; d7d5 c7c6 e7e6 9 | d7d5 c8d7 e7e6 13; d7d5 c8f5 e7e6 8; d7d5 c7c6 g8f6 5 | d7d5 c7c6 c6d5 8; d7d5 c8d7 e7e6 8; c7c5 d8a5 a5c5 6 | c7c6 d7d5 g8f6 12; g8f6 g7g6 f8g7 5; c7c6 d7d5 g7g6 5 | c7c6 d7d5 g8f6 20; c7c6 d7d5 g7g6 8; c7c6 d7d5 c6d5 5 | c7c6 d7d5 g8f6 15; g8f6 g7g6 f8g7 13; c7c6 d7d5 c6d5 12 |
| distinct first-3 sequences per game, white / black | 46% / 49% | 30% / 32% | 28% / 40% | 25% / 41% | 16% / 42% | 22% / 33% | 14% / 31% |
| think percentiles 10/25/50/75/90 at clock > 120 s | 4.0/4.4/5.0/5.7/7.0 | 4.7/4.8/4.8/6.7/7.1 | 5.8/6.0/6.2/8.3/8.9 | 5.8/6.0/6.1/8.1/8.8 | 5.8/6.0/6.2/8.4/8.9 | 5.8/6.0/6.2/8.5/8.9 | 5.7/6.0/6.2/8.4/9.0 |
| **King** king moves share of own moves | 12.9% | 11.5% | 13.9% | 15.6% | 11.7% | 10.3% | 10.4% |
| king steps onto an attacked square (= loss by king move) per 100 king moves | 5.7 | 2.9 | 2.2 | 2.8 | 2.3 | 0.9 | 0.8 |
| king reachable from an unseen square after the move, share of moves / mean such squares | 56% / 2.60 | 61% / 2.90 | 55% / 2.74 | 60% / 3.14 | 49% / 2.28 | 53% / 2.43 | 52% / 2.61 |
| walk-ins (= walked_in losses) per 1000 decisions | 4.20 | 1.96 | 2.28 | 2.26 | 1.17 | 0.37 | 0.49 |
| losses in sample: walked_in / check_unanswered / other | 19 / 29 / 0 | 10 / 19 / 0 | 12 / 14 / 0 | 13 / 18 / 0 | 6 / 13 / 0 | 2 / 4 / 0 | 4 / 7 / 0 |
| checks given per game | 1.4 | 1.9 | 2.1 | 2.2 | 2.1 | 2.4 | 2.2 |
| **Material** unseen-capture pts taken / lost per game | 10.4 / 8.3 | 11.0 / 8.6 | 10.1 / 9.2 | 9.6 / 9.3 | 10.8 / 8.2 | 10.2 / 8.2 | 10.4 / 7.8 |
| all capture pts taken / lost per game | 26.2 / 23.9 | 29.1 / 27.0 | 28.8 / 26.4 | 29.4 / 27.4 | 28.1 / 25.5 | 29.4 / 25.7 | 29.6 / 25.2 |
| unseen share of own / opp captures | 40% / 35% | 38% / 32% | 35% / 35% | 32% / 34% | 38% / 32% | 35% / 32% | 35% / 31% |
| quiet moves onto a square attacked by an unseen piece | 20.8% | 20.2% | 18.6% | 19.1% | 19.4% | 19.0% | 17.6% |
| quiet moves en prise to an unseen piece (undefended or cheaper attacker) | 4.6% | 4.5% | 3.8% | 4.5% | 3.9% | 2.7% | 3.5% |
| moves leaving another piece undefended and attacked by an unseen piece | 13.6% | 13.5% | 10.5% | 11.1% | 8.8% | 8.8% | 9.7% |
| promotions per game | 0.10 | 0.19 | 0.17 | 0.17 | 0.14 | 0.25 | 0.21 |
| **Outcomes** balance at ply 40 in wins (n) / losses (n) | 4.7 (49) / -3.3 (46) | 2.1 (74) / -1.8 (28) | 2.7 (83) / -2.7 (25) | 2.1 (76) / -1.4 (30) | 1.4 (86) / -1.1 (19) | 1.6 (103) / -0.5 (6) | 1.8 (156) / -2.0 (10) |
| ahead at ply 40 share | 45% | 50% | 58% | 46% | 43% | 53% | 49% |
| balance at end in wins / losses | 8.6 / -9.3 | 6.6 / -9.8 | 6.6 / -8.5 | 6.7 / -10.3 | 5.8 / -10.4 | 6.3 / -9.3 | 6.9 / -10.6 |
| game length mean / median (sample) | 75 / 74 | 85 / 79 | 88 / 80 | 96 / 92 | 86 / 82 | 90 / 88 | 91 / 86 |
| wins of <= 20 plies (sample) | 4 | 1 | 1 | 1 | 1 | 0 | 0 |

Per-opponent scores, all games (the opponent's own version changes over time, see notes):

| opponent (score, games) | v1 | v2 | v14 | v16 | v21 | v25 | v30 |
|---|---|---|---|---|---|---|---|
| Knight Vision | 0.34 (80) | 0.49 (372) | 0.55 (180) | 0.57 (766) | 0.61 (262) | 0.77 (968) | 0.93 (14) |
| Strongly Invisible | 0.21 (70) | 0.48 (454) | 0.71 (212) | 0.67 (666) | 0.81 (242) | 0.81 (794) | 0.77 (28) |
| Decent Chess Bot | - | 0.68 (304) | 0.82 (148) | 0.60 (760) | 0.79 (204) | 0.85 (702) | 0.75 (18) |
| Instructors | 0.25 (104) | 0.65 (358) | 0.82 (138) | 0.82 (522) | 0.82 (126) | 0.91 (450) | 1.00 (10) |
| TA Baseline S | 0.70 (102) | 0.91 (236) | 0.96 (70) | 0.97 (274) | 0.99 (62) | 1.00 (208) | 1.00 (8) |
| TA Baseline A | 0.97 (72) | 0.95 (128) | 0.92 (50) | 0.94 (178) | 1.00 (22) | 1.00 (106) | 1.00 (2) |
| TA Baseline P | 0.99 (66) | 0.92 (98) | 0.93 (28) | 0.99 (138) | 1.00 (30) | 0.98 (82) | 1.00 (2) |


Fixed-version yardsticks from the game list: Instructors stayed at v4 throughout; Greek Gift scored 0.25 (v1, 104
games), 0.65 (v2, 358), 0.82 (v14, 138), 0.82 (v16, 522), 0.82 (v21, 126), 0.91 (v25, 450), 1.00 (v30, 10).
Decent Chess Bot v4: 0.56 vs GG v16 (394), 0.79 vs v21 (204). Knight Vision v36: 0.52 vs v16 (98), 0.61 vs v21
(262), 0.77 vs v25 (968). Strongly Invisible v31: 0.21 vs v1 (70), 0.48 vs v2 (454).

## What changed at each jump

**v1 -> v2 (Oct 2; 0.580 -> 0.659; common-opp 0.563 -> 0.646; Instructors v4 0.25 -> 0.65).** Behaviour: (1) the
opening went from 1.e4 Nf3/Nc3 (59/59) to 1.d4 with Bf4/e3 or an early d5 push (58/60), and black always 1...d5
(60/60, from 36/61); variety fell (distinct first-3 sequences 46% -> 30% as white). (2) Time: v1 used half its clock
(88 s left at the end, 1% of games under 20 s) with no fittable rule (median error 0.40 s); v2 has a clock formula,
think = 2 + (clock-15)/max(15, 60-n), already bimodal (4.8 / 6.7 s at a full clock), ending at 60 s, 16% of games
under 20 s. (3) Fatal king moves halved: 5.7 -> 2.9 per 100 king moves, walk-in losses 4.2 -> 2.0 per 1000
decisions, unanswered-check losses 29 -> 19 per 120 games. Material handling did not change (hanging 13.6% -> 13.5%,
en prise 4.6% -> 4.5%, net unseen +2.1 -> +2.4). Pool: v1 played 85% of its games vs staff bots (0.62 there, 0.34 in
80 non-staff games), v2 65%; the population score understates the change (+0.40 on Instructors v4, +0.27 on Strongly
Invisible v31). Reading: a search that stops stepping into attacked squares as often, a 1.d4 repertoire, and a time
rule that uses the clock.

**v2 -> v14 (Oct 4; 0.659 -> 0.768; common-opp 0.646 -> 0.768; Instructors v4 0.65 -> 0.82).** (1) The v30
drain-the-clock rule appears here, exactly: think = 2.5 + (clock-12)/max(15, 46-0.75n) fits v14, v16, v21, v25 and
v30 with the same parameters (0.04-0.05 s median error); clock at ply 40 112 -> 87 s, at ply 80 50 -> 26 s, 38% of
games end under 20 s. Mean think in plies 1-40 5.3 -> 6.7 s. (2) Material discipline begins: hanging-to-unseen
13.5% -> 10.5%, en prise 4.5% -> 3.8%, ahead at ply 40 in 58% of games (50%). (3) King: king-move losses 2.9 -> 2.2,
walk-ins unchanged (2.0 -> 2.3). (4) Same 1.d4 systems; as black 1...c5 appears (15/67). Pool: the same ten
opponents, a few versions newer. Reading: a stronger search that spends the whole clock and hangs fewer pieces to
hidden attackers; the king numbers barely move, so no safe-first rule yet.

**v14 -> v16 (Oct 6-12; 0.768 -> 0.737).** Pool, not behaviour: every behavioural row is within noise of v14 (same
time fit, same openings, hanging 10.5% -> 11.1%, en prise 3.8% -> 4.5%, king-move losses 2.2 -> 2.8). Decent Chess Bot
went from v1 to v4 in this window (GG 0.82 vs DCB v1, 0.56 vs DCB v4 over 394 games) and Knight Vision from v15 to
v36; Instructors v4 stayed at 0.82. v16 has the most king moves (15.6%) and longest games (94 plies, 6.4% draws),
consistent with a harder pool.

**v16 -> v21 (Oct 12; 0.737 -> 0.829; common-opp 0.725 -> 0.829; DCB v4 0.56 -> 0.79; KV v36 0.52 -> 0.61).**
(1) New book, both colours: as white 1.d4 2.c4 cxd5 becomes the main line (17/67, never seen before), variety 16%;
as black 1...d5 is replaced by 1...c6 (25/53) and 1...Nf6 g6 Bg7 (21/53), the v30 repertoire, with the c6/Nf6 split
that time.md reports as the randomness. (2) Material: net unseen-capture gain +0.2 -> +2.6 per game (taken 9.6 ->
10.8, lost 9.3 -> 8.2); hanging 11.1% -> 8.8%, the v25/v30 level. (3) King: walk-in losses halve (2.3 -> 1.2 per
1000; 13 -> 6 per 120 games), unanswered-check losses 18 -> 13. (4) Time unchanged; king moves 11.7%; games 96 -> 86
plies. Pool: all 16 opponents shared with v25; the fixed-version yardsticks (DCB v4 +0.23, KV v36 +0.09) put most of
the gain in behaviour (Instructors is flat at 0.82, a ceiling). Reading: the position tracking became good enough to
take with hidden pieces and stop feeding them, plus the final opening book.

**v21 -> v25 (Oct 16; 0.829 -> 0.889; common-opp 0.829 vs v25's 0.873 on the same opponents; KV v36 0.61 -> 0.77;
Instructors v4 0.82 -> 0.91).** (1) Losses collapse: 19 -> 6 per 120 games (13.5% -> 8.9% in the full lists);
walk-in losses 1.17 -> 0.37 per 1000 decisions and king-move losses 2.3 -> 0.9 per 100 king moves, both about 3x;
unanswered-check losses 13 -> 4. (2) En prise quiet moves 3.9% -> 2.7%, the lowest of any version; hanging and net
unseen captures unchanged (8.8%, +2.6 -> +2.0). (3) Nothing else moved: same time rule, same openings (c6 43 / Nf6
18), same capture volumes, balance at ply 40 in wins +1.4 -> +1.6. Pool: 34 opponents over four weeks; equal scores
vs staff (0.88) and non-staff (0.89); about two thirds of the population gain is behaviour. Reading: a rule that
refuses moves after which the king can be taken in any position the bot holds possible (the safe-first rule) over
an accurate position set. It removes both loss kinds at once, which a search tweak would not, at no cost in material
or clock.

**v25 -> v30 (0.889 -> 0.893).** No behavioural change except 1.9% of moves (own moves 5-8, and two games vs Knight
Vision) played in 0.3 s, which no earlier version has (0.0-0.1%). The first moves of every version take the full
6 s, so the book was never a fast lookup. Everything else is within noise of v25 (loss kinds 4/7 vs 2/4, en prise
3.5% vs 2.7%, hanging 9.7% vs 8.8%). v30's pool is harder: 16% of its games are vs opponents v25 never met, 0.895
vs 0.913 on shared ones.

## Caveats

- Loss-kind counts come from 120-game samples: 6 losses (v25) and 11 (v30) cannot settle the walked-in vs check
  split; the v21 -> v25 drop is backed by the full lists (198/1466 vs 630/7092 losses). Per-move rates rest on
  4,500-8,100 own moves per version and are stable to about one point.
- The king-exposure count shows no trend (49-61%); it tracks game phase, not the safe-first rule, which is visible
  only as the loss rate.
- Opponents upgraded through the period (Knight Vision v9 -> v36, Strongly Invisible v31 -> v42, DCB v1 -> v7), so
  common-opponent scores understate the bot's own improvement; the fixed-version yardsticks are the cleanest
  comparison and agree with the sample metrics on where the jumps are.
- v1's time rule could not be fitted; only v2 and later have a clean clock formula. v15, v17-20, v22-24 and v26-29
  (12-306 games each) were not sampled.
