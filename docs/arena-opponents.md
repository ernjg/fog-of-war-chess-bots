# How the bots that beat us play (arena v4 losses, true-board Stockfish depth 8)

Data: 64 lost games of version 4 (all 'King capturable'), 4914 plies; Greek Gift also on 24 wins against other teams. Stockfish 19, depth 8, multipv 3 on the TRUE board; positions that are illegal in orthodox chess (opponent king attackable) skipped. Random reference = mean of 1/N and 3/N over the legal (pseudo-legal FoW) move count N.

## 1. Engine agreement with Stockfish on the true board

| winner | games | winner plies | winner top-1 | winner top-3 | OUR top-1 | OUR top-3 | random top-1 / top-3 |
|---|---|---|---|---|---|---|---|
| ALL 64 losses | 64 | 2441 | 34% | 61% | 34% | 60% | 3% / 10% |
| winners rated below us | 25 | 971 | 31% | 57% | 37% | 62% | 3% / 10% |
| winners rated above us | 39 | 1470 | 37% | 63% | 32% | 59% | 3% / 10% |
| Resting Bishop Faces (1703) | 6 | 238 | 29% | 61% | 34% | 61% | 3% / 10% |
| Greek Gift (2306) | 6 | 273 | 36% | 65% | 31% | 58% | 3% / 10% |
| duck (1975) | 6 | 185 | 37% | 66% | 36% | 55% | 3% / 8% |
| Strongly Invisible (1996) | 5 | 160 | 39% | 61% | 33% | 56% | 3% / 10% |
| IAmAVirus (1822) | 4 | 172 | 35% | 67% | 38% | 66% | 3% / 9% |
| Knight Vision (1999) | 4 | 137 | 30% | 60% | 26% | 47% | 3% / 8% |
| Gravel Road (1913) | 4 | 196 | 33% | 61% | 32% | 65% | 3% / 10% |
| RATIRL (1754) | 3 | 130 | 35% | 59% | 44% | 66% | 4% / 11% |
| Lost Signal (1706) | 3 | 146 | 25% | 42% | 33% | 59% | 3% / 8% |
| Farsight (2031) | 3 | 115 | 39% | 64% | 32% | 61% | 3% / 9% |
| HYPOTHERMIA (1935) | 3 | 107 | 47% | 72% | 39% | 67% | 4% / 11% |
| Decent Chess Bot (1988) | 3 | 91 | 37% | 60% | 25% | 59% | 3% / 8% |
| Team 319 (1958) | 2 | 79 | 37% | 68% | 29% | 55% | 4% / 11% |
| TUM (1726) | 1 | 34 | 32% | 53% | 29% | 56% | 3% / 8% |
| Ex Republics (1775) | 1 | 41 | 34% | 54% | 39% | 56% | 3% / 8% |
| Instructors (1878) | 1 | 36 | 31% | 56% | 27% | 59% | 4% / 11% |
| Cross-Registered Playe (1792) | 1 | 49 | 39% | 55% | 27% | 53% | 3% / 9% |
| Mist Opportunities (1782) | 1 | 50 | 28% | 44% | 29% | 49% | 4% / 12% |
| Cranberry Lemon (1854) | 1 | 50 | 42% | 66% | 50% | 69% | 4% / 11% |
| TA Baseline A (1495) | 1 | 8 | 12% | 62% | 33% | 44% | 3% / 10% |
| TA Baseline S (1585) | 1 | 25 | 20% | 64% | 46% | 77% | 3% / 9% |
| Trojan Horse (1541) | 1 | 21 | 43% | 67% | 36% | 55% | 3% / 9% |
| sillygeese (1820) | 1 | 34 | 32% | 59% | 41% | 68% | 4% / 11% |
| Mu1tip13 @g3nt$ (1582) | 1 | 23 | 30% | 61% | 70% | 83% | 3% / 9% |
| Crimson Fog (1918) | 1 | 41 | 34% | 56% | 36% | 69% | 4% / 11% |
| Greek Gift vs others (24 wins) | 24 | 1112 | 32% | 61% | 28% | 53% | 3% / 9% |

Agreement by move number (all winners vs us):

| move no. | winner top-1 | winner top-3 | our top-1 | our top-3 |
|---|---|---|---|---|
| 1-10 | 35% | 70% | 44% | 67% |
| 11-20 | 41% | 68% | 35% | 59% |
| 21-30 | 37% | 60% | 29% | 59% |
| 31-45 | 25% | 46% | 29% | 55% |
| 46-200 | 26% | 43% | 28% | 55% |

## 2. Think time (seconds per move from the clocks, +2 s increment)

| winner | mean | median | max | moves 1-10 | 11-20 | 21-30 | 31+ | our mean |
|---|---|---|---|---|---|---|---|---|
| ALL | 4.36 | 4.33 | 15.1 | 5.34 | 5.17 | 3.83 | 3.05 | 4.65 |
| Resting Bishop Faces (1703) | 1.36 | 1.29 | 2.6 | 0.96 | 2.27 | 1.41 | 0.80 | 4.77 |
| Greek Gift (2306) | 4.89 | 5.29 | 9.9 | 6.23 | 6.28 | 5.53 | 3.10 | 4.47 |
| duck (1975) | 5.03 | 5.12 | 10.4 | 5.14 | 5.25 | 4.87 | 4.38 | 5.03 |
| Strongly Invisible (1996) | 4.34 | 4.27 | 14.2 | 4.47 | 4.34 | 4.06 | 4.48 | 4.85 |
| IAmAVirus (1822) | 5.29 | 4.81 | 8.9 | 8.08 | 5.94 | 4.36 | 3.36 | 4.62 |
| Knight Vision (1999) | 4.30 | 4.90 | 6.7 | 2.70 | 5.26 | 4.88 | 4.64 | 4.93 |
| Gravel Road (1913) | 5.24 | 3.32 | 15.1 | 12.25 | 5.77 | 3.31 | 2.28 | 4.41 |
| RATIRL (1754) | 3.10 | 3.25 | 6.1 | 2.10 | 4.08 | 2.84 | 3.32 | 4.24 |
| Lost Signal (1706) | 4.07 | 3.94 | 10.6 | 4.94 | 8.24 | 2.77 | 2.07 | 4.58 |
| Farsight (2031) | 3.33 | 3.14 | 6.9 | 3.18 | 3.43 | 2.69 | 4.12 | 4.94 |
| HYPOTHERMIA (1935) | 5.09 | 5.03 | 7.3 | 6.37 | 5.34 | 4.43 | 3.58 | 4.62 |
| Decent Chess Bot (1988) | 6.18 | 6.12 | 10.0 | 8.44 | 6.40 | 3.85 | 3.44 | 5.10 |
| Team 319 (1958) | 4.95 | 5.04 | 8.7 | 5.17 | 6.28 | 4.92 | 3.56 | 4.69 |
| TUM (1726) | 5.93 | 5.62 | 10.5 | 7.33 | 6.50 | 4.75 | 3.94 | 4.90 |
| Ex Republics (1775) | 4.44 | 4.45 | 6.9 | 4.57 | 5.40 | 4.29 | 3.58 | 4.90 |
| Instructors (1878) | 3.72 | 3.56 | 5.4 | 4.45 | 3.48 | 3.48 | 3.31 | 4.77 |
| Cross-Registered Playe (1792) | 4.81 | 4.50 | 7.7 | 6.90 | 5.49 | 4.48 | 3.52 | 4.52 |
| Mist Opportunities (1782) | 4.66 | 4.35 | 7.7 | 6.71 | 5.22 | 4.21 | 3.59 | 3.59 |
| Cranberry Lemon (1854) | 5.16 | 4.64 | 8.0 | 8.00 | 6.87 | 4.76 | 3.19 | 4.15 |
| TA Baseline A (1495) | 5.12 | 5.15 | 5.4 | 5.12 | - | - | - | 5.89 |
| TA Baseline S (1585) | 4.80 | 4.72 | 5.7 | 5.28 | 4.59 | 4.24 | - | 3.81 |
| Trojan Horse (1541) | 5.67 | 5.04 | 11.7 | 5.24 | 6.31 | 3.62 | - | 4.74 |
| sillygeese (1820) | 5.58 | 5.50 | 8.7 | 6.94 | 5.91 | 4.57 | 3.87 | 4.24 |
| Mu1tip13 @g3nt$ (1582) | 3.59 | 4.29 | 4.4 | 3.24 | 3.81 | 4.03 | - | 4.87 |
| Crimson Fog (1918) | 3.53 | 3.64 | 3.9 | 3.77 | 3.80 | 3.47 | 3.14 | 4.87 |
| Greek Gift vs others | 5.23 | 5.53 | 9.6 | 6.56 | 6.78 | 5.79 | 3.25 | 4.35 |

## 3. The kill

By the rules a side sees exactly the squares it attacks (plus pawn pushes), so a winner that 'sees' our king already wins; the winner saw our king on the frame before the kill in 0/64 games by construction. Instead: how many of the 8 squares around our king it saw.

Two kinds: `check` = the winner's last move attacked our king and we did not answer it; `walked_in` = our own last move put the king on an attacked square or unblocked a line.

**All 64 losses** (64 games)

| | value |
|---|---|
| kind | walked_in: 38, check_unanswered: 26 |
| attacker piece | Q: 28, R: 19, B: 6, K: 5, N: 4, P: 2 |
| R+Q share | 73% |
| attacker distance (king-steps) | 1: 13, 2: 14, 3: 12, 4: 13, 5: 6, 6: 4, 7: 2 (mean 3.1) |
| winner saw our king before the attack | 0/64 |
| king-neighbour squares the winner saw (of 8) | 0: 5, 1: 10, 2: 14, 3: 17, 4: 6, 5: 11, 6: 1 (mean 2.7) |
| of our pieces visible to winner then | mean 1.5 of 5.6 |
| attacking move was a capture (check cases) | 12/26 |
| discovered attack (check cases) | 11/26 |
| plies the attacker was already on the striking line (0 = the attack move brought it there) | 0: 54, 1: 3, 2: 2, 3: 1, 4: 1, 11: 1, 17: 1, 30: 1 |
| we saw the attacker before the fatal ply | 2/64 |
| our fatal move | king_move: 47, other: 13, capture: 4 |
| our king square at death | e7: 5, h2: 4, g1: 3, f5: 3, f8: 3, d2: 3, h7: 3, f7: 3 |
| game length (plies) | mean 77, min 9, max 149 |

**Losses to lower-rated winners** (25 games)

| | value |
|---|---|
| kind | walked_in: 15, check_unanswered: 10 |
| attacker piece | R: 10, Q: 9, B: 3, K: 2, N: 1 |
| R+Q share | 76% |
| attacker distance (king-steps) | 1: 3, 2: 3, 3: 8, 4: 5, 5: 3, 6: 1, 7: 2 (mean 3.5) |
| winner saw our king before the attack | 0/25 |
| king-neighbour squares the winner saw (of 8) | 0: 4, 1: 3, 2: 5, 3: 6, 4: 3, 5: 4 (mean 2.5) |
| of our pieces visible to winner then | mean 1.4 of 5.4 |
| attacking move was a capture (check cases) | 2/10 |
| discovered attack (check cases) | 2/10 |
| plies the attacker was already on the striking line (0 = the attack move brought it there) | 0: 22, 1: 1, 2: 1, 11: 1 |
| we saw the attacker before the fatal ply | 0/25 |
| our fatal move | king_move: 15, other: 8, capture: 2 |
| our king square at death | g1: 2, h2: 2, f5: 2, h6: 1, d7: 1, h8: 1, f8: 1, c5: 1 |
| game length (plies) | mean 78, min 17, max 134 |

**Greek Gift vs us** (6 games)

| | value |
|---|---|
| kind | walked_in: 4, check_unanswered: 2 |
| attacker piece | Q: 3, P: 1, B: 1, R: 1 |
| R+Q share | 67% |
| attacker distance (king-steps) | 1: 3, 2: 1, 4: 2 (mean 2.2) |
| winner saw our king before the attack | 0/6 |
| king-neighbour squares the winner saw (of 8) | 1: 2, 2: 1, 3: 2, 5: 1 (mean 2.5) |
| of our pieces visible to winner then | mean 1.7 of 5.7 |
| attacking move was a capture (check cases) | 2/2 |
| discovered attack (check cases) | 1/2 |
| plies the attacker was already on the striking line (0 = the attack move brought it there) | 0: 4, 2: 1, 4: 1 |
| we saw the attacker before the fatal ply | 0/6 |
| our fatal move | king_move: 6 |
| our king square at death | e7: 2, g5: 1, e8: 1, f1: 1, g3: 1 |
| game length (plies) | mean 92, min 44, max 149 |

**Greek Gift vs others** (24 games)

| | value |
|---|---|
| kind | walked_in: 10, check_unanswered: 14 |
| attacker piece | R: 9, Q: 8, B: 4, N: 2, K: 1 |
| R+Q share | 71% |
| attacker distance (king-steps) | 1: 3, 2: 9, 3: 6, 4: 3, 5: 1, 6: 1, 7: 1 (mean 2.9) |
| winner saw our king before the attack | 0/24 |
| king-neighbour squares the winner saw (of 8) | 1: 2, 2: 4, 3: 9, 4: 4, 5: 3, 7: 2 (mean 3.4) |
| of our pieces visible to winner then | mean 1.3 of 5.5 |
| attacking move was a capture (check cases) | 1/14 |
| discovered attack (check cases) | 6/14 |
| plies the attacker was already on the striking line (0 = the attack move brought it there) | 0: 23, 3: 1 |
| we saw the attacker before the fatal ply | 2/24 |
| our fatal move | king_move: 16, other: 6, capture: 2 |
| our king square at death | h8: 3, g1: 2, e2: 2, g6: 1, b7: 1, f1: 1, b8: 1, h2: 1 |
| game length (plies) | mean 93, min 40, max 209 |

Per opponent (kills):

| winner | n | check / walked_in | pieces | mean dist | line>0 | we saw attacker | our fatal move |
|---|---|---|---|---|---|---|---|
| Resting Bishop Faces (1703) | 6 | 3 / 3 | Q:4 R:1 N:1 | 3.5 | 0 | 0 | king_move:4 capture:1 other:1 |
| Greek Gift (2306) | 6 | 2 / 4 | Q:3 P:1 B:1 R:1 | 2.2 | 2 | 0 | king_move:6 |
| duck (1975) | 6 | 3 / 3 | Q:4 N:1 R:1 | 2.3 | 0 | 1 | king_move:4 other:2 |
| Strongly Invisible (1996) | 5 | 1 / 4 | R:3 P:1 Q:1 | 3.4 | 0 | 0 | king_move:4 other:1 |
| IAmAVirus (1822) | 4 | 2 / 2 | Q:3 R:1 | 3.0 | 0 | 0 | other:2 king_move:2 |
| Knight Vision (1999) | 4 | 2 / 2 | B:2 R:1 Q:1 | 3.8 | 0 | 1 | king_move:4 |
| Gravel Road (1913) | 4 | 0 / 4 | Q:2 N:1 K:1 | 2.8 | 1 | 0 | king_move:3 other:1 |
| RATIRL (1754) | 3 | 0 / 3 | K:2 B:1 | 1.0 | 1 | 0 | king_move:3 |
| Lost Signal (1706) | 3 | 3 / 0 | R:2 B:1 | 4.7 | 0 | 0 | other:2 king_move:1 |
| Farsight (2031) | 3 | 3 / 0 | Q:3 | 2.7 | 1 | 0 | king_move:2 capture:1 |
| HYPOTHERMIA (1935) | 3 | 2 / 1 | N:1 R:1 Q:1 | 2.3 | 1 | 0 | king_move:2 other:1 |
| Decent Chess Bot (1988) | 3 | 2 / 1 | Q:2 R:1 | 4.7 | 2 | 0 | king_move:2 capture:1 |
| Team 319 (1958) | 2 | 0 / 2 | K:1 Q:1 | 2.0 | 0 | 0 | king_move:2 |
| TUM (1726) | 1 | 0 / 1 | R:1 | 4.0 | 0 | 0 | king_move:1 |
| Ex Republics (1775) | 1 | 0 / 1 | R:1 | 5.0 | 0 | 0 | king_move:1 |
| Instructors (1878) | 1 | 0 / 1 | R:1 | 3.0 | 0 | 0 | king_move:1 |
| Cross-Registered Playe (1792) | 1 | 0 / 1 | R:1 | 6.0 | 0 | 0 | king_move:1 |
| Mist Opportunities (1782) | 1 | 0 / 1 | R:1 | 3.0 | 0 | 0 | king_move:1 |
| Cranberry Lemon (1854) | 1 | 0 / 1 | Q:1 | 2.0 | 0 | 0 | king_move:1 |
| TA Baseline A (1495) | 1 | 0 / 1 | Q:1 | 4.0 | 1 | 0 | other:1 |
| TA Baseline S (1585) | 1 | 0 / 1 | B:1 | 3.0 | 0 | 0 | king_move:1 |
| Trojan Horse (1541) | 1 | 0 / 1 | R:1 | 7.0 | 1 | 0 | other:1 |
| sillygeese (1820) | 1 | 1 / 0 | R:1 | 3.0 | 0 | 0 | other:1 |
| Mu1tip13 @g3nt$ (1582) | 1 | 1 / 0 | Q:1 | 3.0 | 0 | 0 | capture:1 |
| Crimson Fog (1918) | 1 | 1 / 0 | K:1 | 1.0 | 0 | 0 | king_move:1 |

## 4. King hunting: do the winner's moves raise pressure on our king zone more than Stockfish would?

kz = number of the 8 squares around our king attacked by the winner on the true board. 'up' = move raises kz; SF column = the same for Stockfish's top-1 move from the same position. R/Q moves: share of moves made with rook or queen, and mean squares the moved R/Q attacks afterwards (open lines).

| winner | plies | kz up (bot) | kz up (SF) | kz down (bot) | kz down (SF) | mean kz after (bot/SF) | R/Q move share (bot/SF) | R/Q mobility after (bot/SF) | moves toward our king |
|---|---|---|---|---|---|---|---|---|---|
| ALL | 2441 | 14% | 16% | 7% | 8% | 0.94 / 0.98 | 29% / 31% | 13.2 / 13.7 | 4.63 |
| rated below us | 971 | 15% | 16% | 8% | 8% | 1.02 / 1.09 | 32% / 34% | 12.8 / 13.2 | 4.68 |
| rated above us | 1470 | 14% | 16% | 6% | 8% | 0.89 / 0.90 | 28% / 28% | 13.5 / 14.1 | 4.60 |
| Resting Bishop Faces (1703) | 238 | 13% | 17% | 6% | 6% | 0.95 / 1.08 | 31% / 39% | 13.3 / 13.7 | 4.72 |
| Greek Gift (2306) | 273 | 12% | 15% | 6% | 8% | 0.90 / 0.90 | 25% / 25% | 12.6 / 12.8 | 4.75 |
| duck (1975) | 185 | 14% | 18% | 4% | 8% | 0.88 / 0.90 | 27% / 25% | 14.0 / 14.3 | 4.63 |
| Strongly Invisible (1996) | 160 | 17% | 16% | 7% | 8% | 0.82 / 0.79 | 29% / 29% | 11.8 / 12.4 | 4.61 |
| IAmAVirus (1822) | 172 | 15% | 15% | 9% | 6% | 0.96 / 1.02 | 40% / 35% | 13.5 / 13.9 | 4.84 |
| Knight Vision (1999) | 137 | 12% | 10% | 7% | 7% | 0.75 / 0.76 | 26% / 28% | 15.1 / 14.7 | 4.84 |
| Gravel Road (1913) | 196 | 12% | 14% | 7% | 9% | 1.04 / 1.04 | 32% / 32% | 13.1 / 14.9 | 4.52 |
| RATIRL (1754) | 130 | 17% | 18% | 9% | 8% | 1.12 / 1.12 | 24% / 23% | 12.1 / 12.6 | 4.59 |
| Lost Signal (1706) | 146 | 14% | 17% | 8% | 12% | 0.88 / 0.92 | 38% / 48% | 13.4 / 14.0 | 4.75 |
| Farsight (2031) | 115 | 11% | 23% | 2% | 4% | 0.74 / 0.93 | 32% / 38% | 13.2 / 16.8 | 4.71 |
| HYPOTHERMIA (1935) | 107 | 16% | 14% | 12% | 13% | 1.07 / 1.00 | 21% / 17% | 14.3 / 14.9 | 4.32 |
| Decent Chess Bot (1988) | 91 | 15% | 16% | 3% | 3% | 0.65 / 0.66 | 27% / 30% | 13.9 / 13.9 | 4.71 |
| Team 319 (1958) | 79 | 15% | 16% | 5% | 4% | 0.87 / 0.91 | 34% / 48% | 14.9 / 13.6 | 4.48 |
| TUM (1726) | 34 | 12% | 38% | 9% | 6% | 0.56 / 1.12 | 32% / 44% | 11.7 / 13.5 | 4.79 |
| Ex Republics (1775) | 41 | 15% | 12% | 7% | 7% | 1.41 / 1.37 | 32% / 15% | 9.3 / 8.7 | 5.02 |
| Instructors (1878) | 36 | 14% | 17% | 11% | 3% | 0.61 / 0.75 | 31% / 19% | 14.5 / 11.9 | 4.50 |
| Cross-Registered Playe (1792) | 49 | 20% | 14% | 16% | 2% | 1.45 / 1.57 | 31% / 22% | 11.3 / 10.8 | 4.55 |
| Mist Opportunities (1782) | 50 | 16% | 20% | 12% | 16% | 1.50 / 1.54 | 32% / 42% | 11.5 / 10.7 | 4.30 |
| Cranberry Lemon (1854) | 50 | 18% | 20% | 16% | 10% | 1.36 / 1.42 | 14% / 14% | 18.0 / 16.6 | 4.02 |
| TA Baseline A (1495) | 8 | 25% | 0% | 12% | 0% | 0.25 / 0.12 | 12% / 0% | 14.0 / nan | 4.75 |
| TA Baseline S (1585) | 25 | 16% | 16% | 8% | 12% | 2.36 / 2.24 | 16% / 24% | 10.8 / 12.3 | 3.56 |
| Trojan Horse (1541) | 21 | 19% | 19% | 5% | 5% | 1.05 / 1.05 | 19% / 19% | 10.5 / 11.2 | 4.76 |
| sillygeese (1820) | 34 | 15% | 6% | 3% | 0% | 0.24 / 0.18 | 29% / 29% | 13.7 / 12.1 | 4.59 |
| Mu1tip13 @g3nt$ (1582) | 23 | 9% | 9% | 9% | 9% | 0.52 / 0.52 | 39% / 17% | 14.7 / 16.0 | 4.74 |
| Crimson Fog (1918) | 41 | 15% | 15% | 10% | 17% | 0.90 / 0.85 | 32% / 29% | 13.6 / 13.0 | 4.39 |
| Greek Gift vs others | 1112 | 14% | 15% | 6% | 7% | 0.94 / 0.93 | 30% / 29% | 12.4 / 12.5 | 4.68 |

(last column = mean king-distance of the moved piece's destination from our king; smaller = closer.)

## 5. Style summary per opponent (their moves in games they beat us)

| winner | games | mean length (their moves) | captures | checks given | Q moves | R moves | N moves | P moves | K moves | castled | their king at end |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | 64 | 38 | 28% | 4% | 14% | 16% | 17% | 27% | 11% | 57/64 | g1:14 g8:6 h1:4 g2:3 |
| OUR moves (reference) | 64 | 39 | 22% | 4% | 8% | 14% | 17% | 31% | 18% | 56/64 |  |
| Resting Bishop Faces (1703) | 6 | 40 | 30% | 4% | 11% | 20% | 13% | 36% | 7% | 5/6 | g1:3 g2:1 a8:1 h1:1 |
| Greek Gift (2306) | 6 | 46 | 23% | 4% | 8% | 17% | 14% | 21% | 22% | 6/6 | b2:1 a8:1 f1:1 h8:1 |
| duck (1975) | 6 | 31 | 31% | 2% | 16% | 11% | 20% | 29% | 9% | 6/6 | h1:2 e6:1 g1:1 f8:1 |
| Strongly Invisible (1996) | 5 | 32 | 28% | 4% | 11% | 18% | 17% | 26% | 7% | 4/5 | c8:1 h2:1 e8:1 g1:1 |
| IAmAVirus (1822) | 4 | 43 | 25% | 3% | 26% | 13% | 22% | 21% | 5% | 4/4 | g8:2 g2:1 b7:1 |
| Knight Vision (1999) | 4 | 34 | 32% | 4% | 18% | 9% | 24% | 31% | 5% | 4/4 | g1:2 f2:1 g8:1 |
| Gravel Road (1913) | 4 | 49 | 26% | 4% | 14% | 18% | 16% | 28% | 10% | 4/4 | g7:1 g2:1 h7:1 d2:1 |
| RATIRL (1754) | 3 | 43 | 28% | 2% | 5% | 19% | 15% | 27% | 15% | 3/3 | g4:1 d4:1 b3:1 |
| Lost Signal (1706) | 3 | 49 | 20% | 5% | 23% | 15% | 10% | 26% | 8% | 2/3 | e5:1 b4:1 f8:1 |
| Farsight (2031) | 3 | 38 | 26% | 8% | 20% | 12% | 18% | 24% | 10% | 3/3 | g1:1 h1:1 g3:1 |
| HYPOTHERMIA (1935) | 3 | 36 | 32% | 8% | 8% | 12% | 20% | 29% | 11% | 2/3 | g8:1 g1:1 g3:1 |
| Decent Chess Bot (1988) | 3 | 30 | 32% | 2% | 16% | 11% | 26% | 29% | 3% | 3/3 | g1:2 g8:1 |
| Team 319 (1958) | 2 | 40 | 30% | 3% | 16% | 18% | 9% | 24% | 16% | 2/2 | d3:1 h2:1 |
| TUM (1726) | 1 | 34 | 32% | 0% | 9% | 24% | 6% | 29% | 3% | 0/1 | e2:1 |
| Ex Republics (1775) | 1 | 41 | 27% | 2% | 2% | 29% | 15% | 22% | 12% | 0/1 | e1:1 |
| Instructors (1878) | 1 | 36 | 28% | 6% | 14% | 17% | 22% | 22% | 8% | 1/1 | a8:1 |
| Cross-Registered Playe (1792) | 1 | 49 | 31% | 4% | 4% | 27% | 18% | 27% | 4% | 1/1 | b8:1 |
| Mist Opportunities (1782) | 1 | 50 | 28% | 6% | 4% | 28% | 16% | 24% | 20% | 1/1 | g5:1 |
| Cranberry Lemon (1854) | 1 | 51 | 25% | 4% | 12% | 2% | 12% | 33% | 24% | 1/1 | h6:1 |
| TA Baseline A (1495) | 1 | 8 | 25% | 12% | 12% | 0% | 12% | 38% | 0% | 0/1 | e8:1 |
| TA Baseline S (1585) | 1 | 25 | 44% | 4% | 4% | 12% | 24% | 12% | 28% | 1/1 | b6:1 |
| Trojan Horse (1541) | 1 | 21 | 33% | 5% | 5% | 14% | 29% | 19% | 5% | 1/1 | c8:1 |
| sillygeese (1820) | 1 | 34 | 29% | 6% | 9% | 21% | 18% | 24% | 3% | 1/1 | g1:1 |
| Mu1tip13 @g3nt$ (1582) | 1 | 23 | 26% | 9% | 30% | 9% | 22% | 22% | 4% | 1/1 | g1:1 |
| Crimson Fog (1918) | 1 | 41 | 24% | 7% | 15% | 17% | 22% | 24% | 15% | 1/1 | d6:1 |
| Greek Gift vs others | 24 | 46 | 23% | 6% | 12% | 18% | 18% | 25% | 6% | 24/24 | g8:4 g1:3 g7:2 h1:2 |

## 6. 'Stockfish on one guessed board'? True board vs the winner's visible board

First test (SF best-move target square visible to the winner) is vacuous: a move's target is always visible to its mover in FoW. Instead: Stockfish depth 8 was also run on the winner's VISIBLE board (our pieces it could not see removed; our king kept, since a FEN needs one). Plies where SF(true) and SF(visible) pick the same move say nothing about information; where they differ, a bot that runs an engine on 'unseen = empty' should follow SF(visible), one that tracks hidden pieces well follows SF(true).

| winner | plies | SF(true)=SF(vis) plies | top-1 | top-3 | differ plies | top-1 TRUE | top-3 TRUE | top-1 VIS | top-3 VIS |
|---|---|---|---|---|---|---|---|---|---|
| ALL | 2441 | 412 | 58% | 80% | 2029 | 30% | 57% | 7% | 22% |
| rated below us | 971 | 167 | 55% | 78% | 804 | 26% | 53% | 8% | 25% |
| rated above us | 1470 | 245 | 60% | 81% | 1225 | 32% | 60% | 6% | 20% |
| Resting Bishop Faces (1703) | 238 | 40 | 52% | 85% | 198 | 24% | 56% | 8% | 22% |
| Greek Gift (2306) | 273 | 49 | 55% | 73% | 224 | 32% | 63% | 4% | 19% |
| duck (1975) | 185 | 29 | 62% | 93% | 156 | 32% | 61% | 7% | 24% |
| Strongly Invisible (1996) | 160 | 25 | 68% | 84% | 135 | 33% | 56% | 5% | 18% |
| IAmAVirus (1822) | 172 | 24 | 62% | 92% | 148 | 31% | 63% | 5% | 20% |
| Knight Vision (1999) | 137 | 21 | 62% | 86% | 116 | 24% | 55% | 6% | 22% |
| Gravel Road (1913) | 196 | 33 | 42% | 70% | 163 | 31% | 59% | 7% | 21% |
| RATIRL (1754) | 130 | 22 | 64% | 77% | 108 | 29% | 56% | 12% | 35% |
| Lost Signal (1706) | 146 | 25 | 36% | 56% | 121 | 23% | 39% | 8% | 21% |
| Farsight (2031) | 115 | 18 | 67% | 89% | 97 | 34% | 60% | 1% | 10% |
| HYPOTHERMIA (1935) | 107 | 18 | 56% | 78% | 89 | 45% | 71% | 8% | 27% |
| Decent Chess Bot (1988) | 91 | 13 | 54% | 85% | 78 | 35% | 56% | 3% | 17% |
| Team 319 (1958) | 79 | 17 | 71% | 94% | 62 | 27% | 61% | 11% | 24% |
| TUM (1726) | 34 | 9 | 44% | 78% | 25 | 28% | 44% | 0% | 28% |
| Ex Republics (1775) | 41 | 4 | 25% | 75% | 37 | 35% | 51% | 3% | 32% |
| Instructors (1878) | 36 | 6 | 67% | 67% | 30 | 23% | 53% | 13% | 13% |
| Cross-Registered Playe (1792) | 49 | 12 | 75% | 92% | 37 | 27% | 43% | 5% | 14% |
| Mist Opportunities (1782) | 50 | 16 | 44% | 50% | 34 | 21% | 41% | 15% | 38% |
| Cranberry Lemon (1854) | 50 | 10 | 90% | 90% | 40 | 30% | 60% | 5% | 15% |
| TA Baseline A (1495) | 8 | 0 | - | - | 8 | 12% | 62% | 12% | 38% |
| TA Baseline S (1585) | 25 | 5 | 80% | 100% | 20 | 5% | 55% | 25% | 50% |
| Trojan Horse (1541) | 21 | 3 | 100% | 100% | 18 | 33% | 61% | 6% | 39% |
| sillygeese (1820) | 34 | 5 | 100% | 100% | 29 | 21% | 52% | 10% | 21% |
| Mu1tip13 @g3nt$ (1582) | 23 | 2 | 0% | 50% | 21 | 33% | 62% | 10% | 29% |
| Crimson Fog (1918) | 41 | 6 | 50% | 67% | 35 | 31% | 54% | 6% | 31% |
| Greek Gift vs others | 1112 | 205 | 46% | 75% | 907 | 29% | 58% | 6% | 21% |

Agreement by how many of our pieces were hidden from the winner (all winners vs us):

| our pieces hidden | plies | top-1 TRUE | top-3 TRUE | top-1 VIS | top-3 VIS |
|---|---|---|---|---|---|
| 0-2 | 104 | 19% | 35% | 16% | 33% |
| 3-5 | 458 | 29% | 49% | 18% | 36% |
| 6-9 | 830 | 38% | 62% | 17% | 32% |
| 10-16 | 1049 | 36% | 68% | 12% | 27% |

Verdict: none of the winners is 'Stockfish on the visible board'. Where information matters they follow the true-board engine 4x more often than the visible-board one, at the same rate we do, so they track hidden pieces about as well as our sampler does. Where information does not matter they agree with depth-8 Stockfish 55-70% top-1, i.e. they are engines (or engine-like searches) of modest depth, not heuristics.

## 7. Our side of the kill: the fatal move

47 of 64 losses end with OUR KING MOVE onto an attacked square (35 not in check before the move, 12 in check by an unseen piece and the king stepped to another attacked square); 13 with another piece moving while an unseen check stood or a line was unblocked; 4 with a capture.

| fatal king moves (47) | value |
|---|---|
| fog exposure of destination (open lines into fog, 0-8): mean origin -> destination | 3.15 -> 3.94 |
| destination more / equally / less exposed than origin | 29 / 12 / 6 |
| a king move that was safe on the true board existed | 41/47 |
| a safe king move with LOWER fog exposure existed | 33/47 |
| we had only the king left (bare king, every move is a king move) | 7/47 |
| some non-king move survived the ply | 28/47 (27 of the 28 non-check cases where we still had another piece) |
| in-check cases: a safe king square existed | 9/12 |
| non-check cases with >= 5 of our pieces still on the board | 18/35 |
| our piece count at death (median) | 5 |

Base rate over all 150 cached games (82 W, 64 L, 4 D): 771 non-castling king moves, 47 fatal. King moves per game: 5.9 in losses vs 3.6 in wins. We stood in check on the true board 210 times; 103 of them by a piece we could not see (we survived 77 of those by chance or inference).

| destination fog exposure (not in check) | king moves | fatal |
|---|---|---|
| 0 | 37 | 0 (0%) |
| 1 | 93 | 2 (2%) |
| 2 | 102 | 6 (6%) |
| 3 | 97 | 5 (5%) |
| 4 | 116 | 3 (3%) |
| 5 | 99 | 11 (11%) |
| 6 | 73 | 4 (5%) |
| 7 | 37 | 4 (11%) |

Candidate rules (non-check king moves only, 654 moves, 35 fatal): 'never more exposed than origin' blocks 288 moves, catches 19/35; 'exposure >= 4 forbidden' blocks 325, catches 22/35; 'must be the least-exposed king square or exposure <= 2' blocks 322, catches 24/35. Exposure alone is a weak filter: the fatal rate is 2-11% at every exposure level. The stronger signal is the situation: median 5 pieces left, our king in the open (e4, f5, f6, d4, c5, g5 ...) while the opponent still has R/Q unaccounted for.

## 8. Recommendations

Sparring partners (what actually beats us):

1. **Belief-board engine, ~4-5 s/move**: Stockfish (depth ~8-10, or a time cap of 2-4 s) on a tracked board (sampled or last-seen with hidden-piece persistence, NOT unseen=empty). This is what the 1900-2300 bots are: 34-39% top-1 / 60-67% top-3 with the true board, 5-7 s in the opening, 3 s after move 30. Greek Gift is this with 6 s early and a long game (46 of its moves per win vs 38 average).
2. **Fast shallow engine, ~1.3 s/move** (Resting Bishop Faces, 1703, 6-1 vs us in 16 games): same style at a fraction of the time, higher capture rate (30%), queen-heavy kills (4/6). Shows the losses are not about search depth.
3. **Long-range slider swing**: in 54/64 kills the attacker reached the striking line with the kill move itself, from 3-4 king-steps away (R/Q in 73%), 11/26 checks were discovered. A partner that scores R/Q moves landing on the rank/file/diagonal of our king's LAST KNOWN or MOST LIKELY square (rather than king-zone pressure, which the winners do not raise more than Stockfish: 14% vs 16%) reproduces the kill mechanism.
4. **Endgame king-walker exploiter**: keep R+Q, play quiet engine moves, and when our king is probably in the open (we have <= 6 pieces) place sliders on open files/ranks through the fog. 47/64 losses end with our king stepping into such a line.

Defence that would have saved the most games: the king-move filter. 47/64 losses are our own king move onto an attacked square; in 41 a safe king square existed, and in 27 of the 28 non-check cases where we still had another piece simply not moving the king survived the ply (7 were bare-king endings, probably lost anyway). Concretely: (a) when a check is possible from an unseen slider, weight king moves by the number of open fog lines through the destination that an unaccounted enemy R/Q/B could occupy (count hidden enemy sliders, not just fog), (b) stop walking the king toward the centre in endgames with few pieces (5.9 king moves per lost game vs 3.6 per won game), (c) when the belief says we may be in check (103 unseen checks in 150 games), treat 'move the king to another square on the same open line' as no escape.

## Appendix: the 64 kills

| game | winner | plies | kind | attacker | from->at | our king | dist | kz seen | line plies | we saw it | our fatal move |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c5nzkeke | Greek Gift (2306) | 144 | walked_in | P | -->h4 | g5 | 1 | 2 | 0 | 0 | king_move |
| d6m2a0hl | Greek Gift (2306) | 60 | check_unanswered | B | d8->c6 | e8 | 2 | 1 | 0 | 0 | king_move |
| ia3966kv | Greek Gift (2306) | 49 | check_unanswered | Q | d1->e1 | f1 | 1 | 1 | 2 | 0 | king_move |
| l98vxdvp | Greek Gift (2306) | 149 | walked_in | Q | -->a7 | e7 | 4 | 3 | 0 | 0 | king_move |
| sl725k86 | Greek Gift (2306) | 103 | walked_in | R | -->c3 | g3 | 4 | 5 | 0 | 0 | king_move |
| yje67p3d | Greek Gift (2306) | 44 | walked_in | Q | -->f6 | e7 | 1 | 3 | 4 | 0 | king_move |
| 5bdljqe0 | Farsight (2031) | 108 | check_unanswered | Q | f2->e2 | d3 | 1 | 5 | 0 | 0 | king_move |
| anqsg3rw | Farsight (2031) | 64 | check_unanswered | Q | c7->a7 | f7 | 5 | 1 | 17 | 0 | king_move |
| jrpmbkw8 | Farsight (2031) | 58 | check_unanswered | Q | e8->f7 | h7 | 2 | 3 | 0 | 0 | capture |
| 473new7c | Knight Vision (1999) | 52 | check_unanswered | Q | f6->d6 | f8 | 2 | 5 | 0 | 1 | king_move |
| 7lmhfh3w | Knight Vision (1999) | 74 | walked_in | B | -->d6 | f8 | 2 | 2 | 0 | 0 | king_move |
| fqi6nnii | Knight Vision (1999) | 47 | check_unanswered | B | g6->a8 | g2 | 6 | 1 | 0 | 0 | king_move |
| v3u89nnp | Knight Vision (1999) | 102 | walked_in | R | -->g1 | g6 | 5 | 2 | 0 | 0 | king_move |
| 3iro04b0 | Strongly Invisible (1996) | 9 | check_unanswered | Q | d5->a5 | e1 | 4 | 0 | 0 | 0 | other |
| hahmd2im | Strongly Invisible (1996) | 88 | walked_in | R | -->h6 | d6 | 4 | 5 | 0 | 0 | king_move |
| md8ayogk | Strongly Invisible (1996) | 67 | walked_in | R | -->f7 | f3 | 4 | 3 | 0 | 0 | king_move |
| u853hbgl | Strongly Invisible (1996) | 69 | walked_in | R | -->d7 | d3 | 4 | 2 | 0 | 0 | king_move |
| uw5c7ntw | Strongly Invisible (1996) | 90 | walked_in | P | -->h4 | g5 | 1 | 5 | 0 | 0 | king_move |
| 0qftza1t | Decent Chess Bot (1988) | 50 | check_unanswered | Q | f4->e1 | e7 | 6 | 1 | 30 | 0 | capture |
| k9sxbs0q | Decent Chess Bot (1988) | 67 | walked_in | Q | -->e3 | g1 | 2 | 3 | 0 | 0 | king_move |
| snmc6oyd | Decent Chess Bot (1988) | 66 | check_unanswered | R | e3->e1 | e7 | 6 | 2 | 1 | 0 | king_move |
| c07zavus | duck (1975) | 48 | check_unanswered | Q | c4->g8 | h7 | 1 | 3 | 0 | 0 | other |
| ug1xgtus | duck (1975) | 75 | check_unanswered | Q | h1->h2 | d2 | 4 | 4 | 0 | 0 | other |
| w2uwgc2u | duck (1975) | 71 | walked_in | Q | -->h4 | h2 | 2 | 3 | 0 | 0 | king_move |
| wf74zxul | duck (1975) | 72 | check_unanswered | N | e7->d6 | f7 | 2 | 3 | 0 | 1 | king_move |
| wnnjfonx | duck (1975) | 48 | walked_in | Q | -->f7 | d7 | 2 | 5 | 0 | 0 | king_move |
| zh85lga6 | duck (1975) | 59 | walked_in | R | -->c2 | f2 | 3 | 3 | 0 | 0 | king_move |
| 5odocmba | Team 319 (1958) | 105 | walked_in | K | -->d3 | d2 | 1 | 2 | 0 | 0 | king_move |
| es7cg4a2 | Team 319 (1958) | 54 | walked_in | Q | -->d4 | g7 | 3 | 2 | 0 | 0 | king_move |
| 47daxfz0 | HYPOTHERMIA (1935) | 63 | check_unanswered | N | g7->e6 | c5 | 2 | 2 | 0 | 0 | other |
| m7o7qshg | HYPOTHERMIA (1935) | 95 | walked_in | Q | -->d7 | c7 | 1 | 4 | 0 | 0 | king_move |
| prxw2wh6 | HYPOTHERMIA (1935) | 58 | check_unanswered | R | d7->c7 | g7 | 4 | 1 | 1 | 0 | king_move |
| pbmesn55 | Crimson Fog (1918) | 83 | check_unanswered | K | f6->d6 | e5 | 1 | 3 | 0 | 0 | king_move |
| 1reyyvzu | Gravel Road (1913) | 74 | walked_in | K | -->d2 | e3 | 1 | 3 | 0 | 0 | king_move |
| en3le8xt | Gravel Road (1913) | 139 | walked_in | Q | -->b3 | g3 | 5 | 2 | 0 | 0 | king_move |
| spsnca34 | Gravel Road (1913) | 83 | walked_in | Q | -->e5 | h2 | 3 | 1 | 3 | 0 | other |
| ufz1bf3k | Gravel Road (1913) | 98 | walked_in | N | -->c6 | e7 | 2 | 6 | 0 | 0 | king_move |
| 0z9iocct | Instructors (1878) | 73 | walked_in | R | -->f8 | f5 | 3 | 5 | 0 | 0 | king_move |
| xw8ticrp | Cranberry Lemon (1854) | 103 | walked_in | Q | -->e1 | c3 | 2 | 4 | 0 | 0 | king_move |
| czfre8ss | IAmAVirus (1822) | 83 | check_unanswered | Q | c1->h1 | e4 | 3 | 4 | 0 | 0 | other |
| okwir4i9 | IAmAVirus (1822) | 99 | walked_in | Q | -->e5 | h2 | 3 | 1 | 0 | 0 | king_move |
| tzvosfpn | IAmAVirus (1822) | 71 | check_unanswered | Q | d1->h5 | h2 | 3 | 2 | 0 | 0 | other |
| xi7tak8t | IAmAVirus (1822) | 94 | walked_in | R | -->f4 | f7 | 3 | 2 | 0 | 0 | king_move |
| bi696j7h | sillygeese (1820) | 68 | check_unanswered | R | d1->d7 | g7 | 3 | 0 | 0 | 0 | other |
| 80sikvrd | Cross-Registered P (1792) | 99 | walked_in | R | -->a2 | g2 | 6 | 4 | 0 | 0 | king_move |
| vvtx7dnh | Mist Opportunities (1782) | 101 | walked_in | R | -->d5 | d2 | 3 | 3 | 0 | 0 | king_move |
| uposo0wn | Ex Republics (1775) | 82 | walked_in | R | -->a8 | f8 | 5 | 5 | 0 | 0 | king_move |
| a2wcqktj | RATIRL (1754) | 89 | walked_in | B | -->e4 | f5 | 1 | 1 | 2 | 0 | king_move |
| g2wuy29x | RATIRL (1754) | 68 | walked_in | K | -->d4 | c5 | 1 | 5 | 0 | 0 | king_move |
| izged4e2 | RATIRL (1754) | 104 | walked_in | K | -->g4 | f5 | 1 | 5 | 0 | 0 | king_move |
| za0m162t | TUM (1726) | 68 | walked_in | R | -->d3 | d7 | 4 | 2 | 0 | 0 | king_move |
| 3yzf7wps | Lost Signal (1706) | 134 | check_unanswered | B | b7->c2 | h7 | 5 | 3 | 0 | 0 | king_move |
| bkhgwijx | Lost Signal (1706) | 88 | check_unanswered | R | g7->g8 | c8 | 4 | 3 | 0 | 0 | other |
| l8ma5ub5 | Lost Signal (1706) | 71 | check_unanswered | R | b4->b1 | g1 | 5 | 0 | 0 | 0 | other |
| 3sx6otue | Resting Bishop Fac (1703) | 122 | walked_in | R | -->e1 | e8 | 7 | 3 | 0 | 0 | king_move |
| 5mixvf8t | Resting Bishop Fac (1703) | 80 | walked_in | Q | -->h2 | h6 | 4 | 5 | 0 | 0 | king_move |
| feqywbbe | Resting Bishop Fac (1703) | 73 | check_unanswered | Q | d2->e1 | g1 | 2 | 0 | 0 | 0 | capture |
| gfhr17t0 | Resting Bishop Fac (1703) | 68 | walked_in | N | -->d5 | f6 | 2 | 2 | 0 | 0 | king_move |
| hppe85zo | Resting Bishop Fac (1703) | 62 | check_unanswered | Q | d7->e4 | g6 | 2 | 3 | 0 | 0 | king_move |
| q2k012wb | Resting Bishop Fac (1703) | 72 | check_unanswered | Q | d5->d8 | h8 | 4 | 3 | 0 | 0 | other |
| j9gg5mue | TA Baseline S (1585) | 51 | walked_in | B | -->c5 | f2 | 3 | 4 | 0 | 0 | king_move |
| abfstiqy | Mu1tip13 @g3nt$ (1582) | 46 | check_unanswered | Q | h4->d8 | g8 | 3 | 1 | 0 | 0 | capture |
| 9fgbwszk | Trojan Horse (1541) | 43 | walked_in | R | -->d8 | d1 | 7 | 2 | 1 | 0 | other |
| upmhks0f | TA Baseline A (1495) | 17 | walked_in | Q | -->a5 | e1 | 4 | 0 | 11 | 0 | other |
