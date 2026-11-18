# Greek Gift (v30): king handling and endgames, from 179 arena replays

Data: `gg_games.pkl` (179 Greek Gift v30 games, 163-5-11; 8,110 GG moves) and `replays_cache.pkl`
(150 games of our v4 "Magnus Monte Carlsen", 82-4-64; 5,858 moves). Four populations: **GG**,
**GGopp** (its opponents in those games), **US** (v4), **USopp** (our opponents). Six games appear
in both sets (GG vs us).

Definitions. *Phase*: open = ply <= 20, mid = 21-60, end = > 60. *Pieces* = own Q+R+B+N (king and
pawns excluded). *Exposure* = rook-ray + bishop-ray unseen squares with an open line to the king,
`exposure()` from `bots/eBotI/eBotI/hazard.py`, evaluated on the mover's own view after its move.
*Check* = after the opponent's move an enemy piece attacks the king on the true board; *unseen
check* = every such attacker stands on a `?` square of the mover's view. A fatal move is one that
leaves the own king attackable (every "King capturable" loss). Scripts and raw output:
`scratchpad/gg/king/king_analysis.py`, `followup.py`, `unseen_detail.py` and their `*_output.txt`.

## Headline

- GG moves its king **half as often** as anyone else: 10.4% of all moves (opponents 17.9%, us 15.3%);
  in the endgame 17.7% vs 34.0%/34.5%; with 1-2 pieces 20.4% vs 26.5%/23.9%; with 0 pieces 49.7% vs
  69.0%/67.0%.
- Its king steps onto an attacked square in **1.1%** of its king moves (7 of 665); opponents 7.7%,
  us 6.1%. Seven of its 11 losses are that step, and in 5 of the 7 a safe king square existed.
- It does **not** pick low-exposure squares: its chosen king destination is the minimum-exposure
  option 34% of the time (opponents 41%, us 32%), and after moves with 1-2 pieces its king exposure
  (5.6) is *higher* than its opponents' (4.6). Its lower average exposure (2.05 vs 2.50 vs 2.85)
  comes from the opening/middlegame and from the king staying home.
- Unseen checks: it receives one per 175 moves (opponents: one per 38). When it does, it survives
  40 of 45; it **interposes in 23 of 45** (51%; opponents 17%, us 30%), spending its normal 5-6 s,
  so it is reasoning about the hidden attacker, not guessing.
- Endgame wins (161): the enemy king is caught by a **slider at distance >= 2 on an open line in
  73%** (118), adjacent slider 11%, knight 8%, the loser's king walking next to GG's king 6%, pawn 1%.
  The attacker was unseen by the loser before its last move in 154/161 (96%); in 100/161 (62%) the
  loser's own king stepped onto the attacked square. Promotion is a side show (34 of 161 wins had
  any promotion; 3 ended with 2+ queens).
- Pawn shield: GG keeps slightly more pawns next to the king than its opponents (1.49 vs 1.40
  adjacent, all moves) but not more than we do (1.58); the difference is small and mostly phase mix.

## Q1. King moves

### King-move share by phase (castling included)

| pop | open (<=20) | mid (21-60) | end (>60) | all |
|---|---|---|---|---|
| GG | 6.3% (113/1790) | 5.9% (196/3320) | **17.7%** (532/3000) | **10.4%** (841/8110) |
| GGopp | 6.3% (112/1790) | 9.4% (314/3329) | 34.0% (1042/3066) | 17.9% (1468/8185) |
| US | 5.5% (82/1494) | 7.9% (204/2594) | 34.5% (611/1770) | 15.3% (897/5858) |
| USopp | 6.7% (100/1492) | 11.8% (307/2605) | 33.9% (600/1768) | 17.2% (1007/5865) |

### King-move share by own piece count (Q+R+B+N), castling excluded

| pop | 7 | 5-6 | 3-4 | 1-2 | 0 |
|---|---|---|---|---|---|
| GG | 0.3% | 2.0% | 7.0% (145/2061) | **20.4%** (407/1999) | **49.7%** (78/157) |
| GGopp | 0.7% | 4.1% | 11.8% (203/1726) | 26.4% (565/2137) | 69.0% (465/674) |
| US | 0.2% | 1.6% | 7.3% (87/1190) | 23.9% (369/1541) | 67.0% (292/436) |
| USopp | 0.8% | 6.2% | 10.8% (142/1318) | 24.7% (345/1394) | 77.1% (316/410) |

Both sides with 1-4 pieces: GG 13.6% (470/3461), GGopp 21.0%, US 17.5%, USopp 17.9%.
(The 49% figure in the brief for us comes from a different piece definition; by this one we are at
24% with 1-2 pieces and 67% with none. The ordering GG < US < opponents holds either way.)

### Where the king lives (white perspective, black mirrored)

| pop | ply 20 | ply 40 | ply 60 |
|---|---|---|---|
| GG | g1 58%, e1 37%, c1 4% (rank 1: 176/179) | g1 71%, h1 10%, e1 6%, b1 4%, c1 4% (rank 1: 162/171) | g1 45%, h1 14%, g2 11%, h2 6%, f2 4%, f1 4% (rank 1: 98, rank 2: 36, rank 3: 5 of 139) |
| GGopp | g1 51%, e1 40% | g1 58%, b1 8%, g2 7%, c1 7% | g1 35%, h1 12%, g2 7%, b1 6% (rank 1: 93, 2: 37, 3: 9) |
| US | g1 51%, e1 46% | g1 70%, c1 8%, e1 4%, b1 4% | g1 41%, g2 9%, b1 8%, h2 6% (rank 1: 62, 2: 25, 3: 13, 4: 3 of 103) |

GG's king is on g1/h1/g2/h2 at ply 60 in 76% of games; ours is more spread (b1, b2, rank 3-4).

### Castling

| pop | castled | median ply | O-O / O-O-O | castling ply by decade |
|---|---|---|---|---|
| GG | **166/179 (92.7%)** | 17 (min 8, max 47) | 149 / 17 | <10: 17, 10s: 93, 20s: 48, 30s: 6, 40s: 2 |
| GGopp | 151/179 (84.4%) | 17 | 125 / 26 | <10: 5, 10s: 95, 20s: 39, 30s: 10, 40s: 2 |
| US | 126/150 (84.0%) | 17.5 | 105 / 21 | <10: 1, 10s: 77, 20s: 39, 30s: 6, 40s: 3 |
| USopp | 110/150 (73.3%) | 20 | 89 / 21 | 10s: 59, 20s: 34, 30s: 11, 40s: 6 |

First non-castling king move: GG makes one in 132/179 games, median ply 50 (3 before ply 20,
33 in 21-40, 96 after 40). Opponents: 167/179, median 47. Us: 111/150, median 52.

## Q2. King exposure after own moves

### Mean exposure (unseen rook-ray + bishop-ray squares) by phase

| pop | open | mid | end | all | moves with exposure 0 | >= 6 | >= 10 |
|---|---|---|---|---|---|---|---|
| GG | **0.30** | **0.72** | **4.57** (med 4) | **2.05** | 57.3% | 15.5% | 4.9% |
| GGopp | 0.48 | 0.98 | 5.31 (med 5) | 2.50 | 53.2% | 18.8% | 8.0% |
| US | 1.05 | 1.39 | 6.52 (med 6) | 2.85 | 45.5% | 21.1% | 8.6% |
| USopp | 0.55 | 1.40 | 5.83 (med 5) | 2.52 | 49.0% | 17.6% | 7.8% |

Components (all moves): GG rook 1.20 / bishop 0.85 / knight 0.91; GGopp 1.51 / 0.98 / 1.01;
US 1.80 / 1.06 / 1.17. Our opening exposure (1.05) is 3.5x GG's (0.30): we open lines to our own
king early.

### Mean exposure by own piece count

| pop | 7 | 5-6 | 3-4 | 1-2 | 0 |
|---|---|---|---|---|---|
| GG | 0.24 | 0.29 | 1.37 | **5.59** | 10.15 |
| GGopp | 0.41 | 0.44 | 1.15 | 4.59 | 10.52 |
| US | 0.94 | 0.52 | 1.40 | 5.57 | 10.24 |
| USopp | 0.44 | 0.58 | 1.64 | 4.78 | 11.14 |

Controlled for material, GG's king is **not** on fewer unseen lines than its opponents' once it has
1-2 pieces (5.59 vs 4.59). The overall gap is composition (GG spends 157 moves with 0 pieces, its
opponents 674) plus the quieter opening.

### King moves: origin vs destination (non-castling)

| pop | n | exp at origin (pre view) | at destination, judged on the pre view | at destination (post view) | dest < origin | = | > |
|---|---|---|---|---|---|---|---|
| GG | 675 | 5.16 | 6.33 | 5.54 | 27.6% | 18.7% | 53.8% |
| GGopp | 1317 | 6.68 | 7.71 | 6.76 | 29.5% | 16.6% | 53.9% |
| US | 771 | 7.26 | 8.94 | 7.58 | 25.7% | 11.8% | 62.5% |
| USopp | 897 | 6.74 | 7.82 | 6.97 | 28.9% | 17.8% | 53.3% |

Everyone's king moves go to squares with *more* unseen lines than the origin (a king that steps
off the edge sees more squares but also opens more lines). GG is no exception.

### Chosen destination vs the other available king squares (pre-move view)

| pop | king moves | chosen exposure | mean of alternatives | chosen is the minimum | chosen <= median | chosen is the maximum | **destination attacked on true board** |
|---|---|---|---|---|---|---|---|
| GG | 665 | 6.42 | 6.67 | 34.3% | 69.0% | 23.9% | **7 (1.1%)** |
| GGopp | 1303 | 7.78 | 8.44 | 41.5% | 69.5% | 20.9% | 100 (7.7%) |
| US | 765 | 9.01 | 9.23 | 31.6% | 65.2% | 21.3% | 47 (6.1%) |
| USopp | 889 | 7.88 | 8.57 | 40.8% | 72.0% | 20.4% | 51 (5.7%) |

GG's choice of king square is indifferent to the exposure count. What differs is the last column:
its king steps onto an attacked square 6x less often per king move, and it makes half as many
king moves. Exposure in won vs lost games: GG 2.00 vs 2.77; us 2.56 vs 2.94.

## Q3. King attacked by an unseen enemy piece

### Checks after the opponent's move

| pop | games | checks | unseen-attacker checks | survived | died | games with >= 1 unseen check | seen checks | died after a seen check |
|---|---|---|---|---|---|---|---|---|
| GG | 179 | 172 | **45** | 40 | 5 | 17.3% | 114 | 2/114 |
| GGopp | 179 | 399 | 218 | 147 | 71 | 70.9% | 181 | 33/181 |
| US | 150 | 212 | 103 | 87 | 16 | 44.0% | 107 | 10/107 |
| USopp | 150 | 329 | 131 | 103 | 28 | 49.3% | 192 | 30/192 |

Unseen checks per 100 own moves: GG 0.57 (open 0.56, mid 0.54, end 0.60); GGopp 2.66 (0.28 /
1.80 / **4.99**); US 1.76 (1.47 / 1.16 / 2.88); USopp 2.25. GG's opponents get checked from the
fog five times per 100 endgame moves; GG's rate is flat across the game.

In all populations the attacker had just moved (GG 45/45, opponents 211/218): unseen checks are
delivered by a piece arriving on the line, not by the king stepping into a standing one (that is
counted under fatal moves below). Attacker types against GG: Q 20, R 16, B 7, N 2.

### Reply to an unseen check

| pop | n | king moved, ok | interposed, ok | captured | other move, lost | king moved, lost |
|---|---|---|---|---|---|---|
| GG | 45 | 17 | **23 (51%)** | 0 | 3 | 2 |
| GGopp | 218 | 109 | 38 (17%) | 0 | 52 | 19 |
| US | 103 | 56 | 31 (30%) | 0 | 12 | 4 |
| USopp | 131 | 82 | 21 (16%) | 0 | 17 | 11 |

The interpositions are deliberate. GG spends 5.6 s on them (its game average 5.3 s; its king-move
replies take 3.7 s), the attacker's origin square was visible to GG only 5 of 23 times, and the
chance that an unrelated move lands between the king and an open unseen line is 3.9% (measured on
GG's non-king moves when not in check). The cases are textbook: Qa5+ -> Nc3 (3x), Bb5+ -> Bd7/Nc6
(3x), Bb4+ -> c3 (2x), Bh4+ -> g3 (2x), Qa4+ -> Bd7/Nc6 (2x), and in the endgame Ra7+ -> Nb7,
Re5+ -> Ne6, Qg4+/Qe6+ -> Qg7/Qf7 four times in a row (pm3e1zaq, drawn by repetition). GG's
belief evidently contains the checking piece even though its view does not. Reply to a seen
check: GG captures the attacker 75/114, moves the king 38 (2 fatal); we move the king 59/107 and
capture 46.

### Fatal moves (every "King capturable" loss)

| pop | fatal | own king stepped onto attacked square | ...with a safe king square available | stayed under an existing attack | other (uncovered a line) | attacker unseen pre-move | attacker unseen in own post-move view |
|---|---|---|---|---|---|---|---|
| GG | 11 | 7 | 5 | 3 | 1 | 11/11 | 8/11 |
| GGopp | 163 | 100 | 63 | 60 | 3 | 155/163 | 129/163 |
| US | 64 | 47 | 41 | 14 | 3 | 63/64 | 50/64 |
| USopp | 81 | 52 | 34 | 28 | 1 | 70/81 | 62/81 |

GG's 11 losses by ply: 38, 48, 70, 81, 83, 105, 109, 114, 126, 134, 136; attackers Q 5, R 4, N 2.
GG had 0 pieces in 7 of them, 1 piece in 3 and 3 pieces in 1 (ir53fzsx, ply 48, 3 vs 3); the
opponent had 1-4 pieces in every one. Three losses are unseen checks answered with an unrelated
move (Farsight Rd8-f8 at ply 38, HYPOTHERMIA Rb7 at 48, Cranberry Lemon Rf7 at 136), four are
king moves made while already in check (2 seen, 2 unseen), three are king steps into a standing
unseen line with no prior check (9kzu5eir, 7yrrmn79, ww2ykpkn) and one opened a line with a
non-king move (amxeg49b). The "stepped into a standing line with no prior check" count, the
pattern behind most of our losses, is 3 of 11 for GG, 56 of 163 for its opponents, 35 of 64 for
us and 22 of 81 for our opponents.

Fatal king steps with a safe king square available: GG 5 of 7, us 41 of 47. Our problem is not
only that we step into lines, it is that we step into them 6x more often per king move (above)
and make 1.5x more king moves.

## Q4. Endgames (either side has 1-4 pieces)

| pop | games reaching one | W/D/L there | mean length (plies) | median | king-move share | king moves toward / away from enemy king | own-king-to-enemy-king distance at entry / at end | own Q/R/B/N mean distance to own king / to enemy king |
|---|---|---|---|---|---|---|---|---|
| GG | 177/179 | 161/5/11 | 51.2 | 41 | **14.0%** | 283 / 140 (2.0:1) | 6.86 / 5.22 | 3.28 / 5.08 |
| GGopp | 177/179 | 11/5/161 | 51.2 | 41 | 26.4% | 518 / 357 (1.5:1) | 6.86 / 5.16 | 3.08 / 5.38 |
| US | 142/150 | 76/4/62 | 46.1 | 41 | 21.0% | 349 / 203 (1.7:1) | 6.87 / 5.15 | 3.47 / 4.85 |
| USopp | 142/150 | 62/4/76 | 46.1 | 41 | 22.7% | 313 / 211 (1.5:1) | 6.87 / 5.25 | 3.20 / 5.18 |

Per endgame move:

| pop | moves | king | moves that attack the enemy king on the true board | ...with the attacker unseen by the enemy | Q/R/B moves | N | pawn moves | promotions |
|---|---|---|---|---|---|---|---|---|
| GG | 4377 | 14.0% | **7.5%** | **4.5%** | 55.2% | 11.0% | 19.9% | 30 |
| GGopp | 4482 | 26.4% | 2.8% | 0.7% | 45.1% | 7.5% | 21.0% | 6 |
| US | 3124 | 21.0% | 7.3% | 3.1% | 44.8% | 9.5% | 24.6% | 36 |
| USopp | 3131 | 22.7% | 5.2% | 2.5% | 45.8% | 10.6% | 20.9% | 11 |

Who is short when the endgame starts: GG is the side with <= 4 pieces in 59 games (W/D/L 50/2/7,
mean length 51), the opponent in 118 (111/3/4, length 51). Us: 71 (23/2/46; a win takes 65
plies, a loss 44) and 71 (53/2/16; a win takes 35 plies). GG wins 85% even when it traded down
first; we win 32%.

How GG plays it: the king stays home (81% of endgame moves leave it on ranks 1-2, 65% on the
g/h files, 62% in the a/b/g/h corner block; opponents 86% / 60% / 61%, us 79% / 59% / 57%), the
king moves it does make go toward the enemy king 2:1, and its sliders do the hunting: 55% of its
endgame moves are Q/R/B moves (vs 45%) and 7.5% of all its endgame moves put an attack on the
enemy king, 4.5% from a square the enemy cannot see. Its pieces sit on average 3.3 squares from
its own king and 5.1 from the enemy king: not held back, but not thrown forward either.

### How the 161 endgame wins end

| mechanism | GG wins | of which the loser's king stepped into it | US wins (75) | USopp wins (64) |
|---|---|---|---|---|
| slider at distance >= 2 on an open line | **118 (73%)** | 65 | 53 (71%) | 45 (70%) |
| slider adjacent to the king | 18 | 13 | 16 | 6 |
| knight | 13 | 10 | 5 | 4 |
| loser's king walked next to GG's king | 10 | 10 | 1 | 5 |
| pawn | 2 | 2 | 0 | 2 |

Final attacker types: Q 65, R 64, N 13, K 10, B 9, P 3. Attack distance (Chebyshev) 1: 31,
2: 47, 3: 31, 4: 18, 5: 17, 6: 12, 7: 5. GG's last-moved piece: Q 73, R 45, P 16, K 10, B 9, N 8.
Attacker unseen by the loser before its last move: 154/161; still unseen after it: 127/161. GG's
king was at distance 4-7 from the loser's king in 137 of 161 wins (mean 5.2). Promotion: GG
promoted in 33/179 games (we in 34/150); 34 of its 161 endgame wins had a promotion; 3 ended with
two queens. Material at the end: GG 2.4 pieces, loser 1.2. Mean length of a GG win: 91 plies.

Its 11 losses and 5 draws: all endgames; GG had 0 pieces in 6 losses, 1 in 3, 3 in 1. Draws by
repetition at plies 63-175 with 1-3 pieces each.

## Q5. Pawn shield

Own pawns on the 3 squares in front of the king / on the 8 adjacent squares, after own moves:

| pop | open | mid | end | all | mid moves with 0 adjacent pawns |
|---|---|---|---|---|---|
| GG | 1.74 / 1.75 | 1.68 / 1.75 | **0.72 / 1.05** | 1.34 / 1.49 | 6.8% |
| GGopp | 1.70 / 1.70 | 1.62 / 1.72 | 0.65 / 0.89 | 1.27 / 1.40 | 10.0% |
| US | 1.63 / 1.63 | **1.86 / 1.97** | 0.56 / 0.97 | 1.41 / 1.58 | 5.5% |
| USopp | 1.63 / 1.65 | 1.49 / 1.63 | 0.62 / 0.85 | 1.26 / 1.40 | 15.0% |

By own piece count (front / adjacent): GG 7: 1.84/1.84, 5-6: 1.76/1.79, 3-4: 1.17/1.34, 1-2:
0.69/1.05, 0: 0.37/0.88; US 1.79/1.80, 1.96/1.96, 1.65/1.82, 0.71/1.14, 0.35/0.68; GGopp
1.79/1.79, 1.65/1.69, 1.27/1.41, 0.79/1.05, 0.40/0.66. Own pawn count by phase: GG 7.6 / 6.2 /
4.7, us 7.2 / 5.6 / 3.7.

GG keeps a marginally better shield than its opponents (+0.1 pawn) and a worse one than we do in
the middlegame (we sit behind an intact f/g/h chain more often: 1.97 vs 1.75). The shield is not
where GG's edge is; it keeps more pawns overall in the endgame (4.7 vs 3.7) because it trades
pieces, not pawns.

## What this says about the difference

1. GG's king does nothing: 10% of moves, 1.1% of them onto an attacked square. Ours moves 15%
   of the time and 6.1% of those steps are fatal; that alone accounts for 47 of our 64 losses.
2. GG does not minimise unseen lines; it keeps the king home (g1/h1 corner) and trusts its belief
   to tell it when a line is occupied. Half its replies to invisible checks are interpositions,
   which is impossible without a belief that places the checking piece.
3. In the endgame GG hunts with sliders from the fog (7.5% of its endgame moves attack the enemy
   king, 4.5% invisibly) while its own king stays on ranks 1-2; 73% of its endgame wins are a
   slider on an open line at distance 2+, and 62% of all wins are the enemy king stepping into the
   line. Its opponents, and we, lose the same way.
4. Pawn shield and promotion are not differentiators.
