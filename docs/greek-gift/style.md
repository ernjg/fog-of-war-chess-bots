# Greek Gift v30: how it chooses moves, vs Stockfish on the true board, vs its opponents, vs our v4

Scripts and caches: `gg/ea/extract.py` (per-move rows from the replays, rules via `starter/referee.py`), `gg/ea/sf.py` (Stockfish depth 8 multipv 3 on the pre-move true board, 2 engine processes), `gg/ea/evalpass.py` (depth-8 evals after the bot's move and after SF's top-1), `gg/ea/report.py` (all tables, written to `gg/ea/tables.md` and copied below).

Sample: 60 random Greek Gift v30 games (54 wins, 3 losses, 3 draws; 5,427 plies) and 40 random v4 games from our cache (21 wins, 19 losses; 3,252 plies). Caveat for every comparison: Greek Gift's sample is 90% wins against bots rated below it; ours is 50/50. Measures that depend on the game state (opponent king moves, late-game vision) partly reflect who was winning.

## Answers

**1. Agreement with true-board Stockfish.** Greek Gift is NOT more Stockfish-like than we are in move choice: top-1 33% / top-3 62% (n=2703) vs our v4 37% / 62% (n=1624); its opponents 27% / 53%, ours 32% / 58%. In the opening (plies 1-20) we match SF far more often (50% vs 37% top-1), equal in 21-40 (40 vs 39), equal after 40 (30 vs 29). But its deviations cost less on the true board: mean centipawn loss vs SF top-1 is 31 cp (GG) vs 42 (v4), 44 (GG's opponents), 43 (ours); in the opening 14 vs 29 cp; moves losing >300 cp: 2% vs 3%. In what way it differs from SF (plies where its move is not SF's top-1, bot / SF): fewer captures (12% / 16%), fewer checks (3% / 6%), fewer pawn moves (26% / 31%), fewer moves to attacked squares (21% / 29%), more king moves (11% / 8%), slightly lower vision (34.4 / 34.7 squares) and slightly lower king exposure (2.13 / 2.29). Our deviations go the other way on the risk axis: more moves to attacked squares than SF (31% / 25%), more king moves (17% / 11%), fewer queen moves (11% / 19%). When in check from a piece it can see, Greek Gift plays SF's top-1 84% and top-3 100% of the time (v4 70% / 91%); from an unseen attacker 47% / 87% (v4 31% / 67%).

**2. Move types.** GG: captures 22%, checks 5%, king moves 8%, queen moves 13%, pawn moves 28%, castling 2% (castles in 92% of games, mean ply 17.7, 93% kingside). v4: 23 / 6 / 12 / 11 / 29 / 2% (castles in 80%, ply 20). GG's opponents move the king 17% of the time (27% after ply 40) because they are being hunted; GG's checks are 44% by the queen. Moves to a square attacked by an unseen enemy piece: GG 24% of moves, v4 30%, GG's opponents 25%, ours 25%. Nearly all of these are trades or pawn moves; the dangerous kind (an undefended non-pawn, non-capture, non-king move onto an unseen-attacked square) is 0.1% for GG (4 of 2704) vs 1.0% for v4 (16 of 1627); a king stepping onto an attacked square: 2 vs 11. Opening repertoire (all 179 games): as white always 1.d4 (c4 or Nc3+Bf4 next), as black ...Nf6 g6 Bg7 O-O or ...c6 d5; it never opens the e-file. v4 plays 1.e4 and ...d5.

**3. Vision.** After its moves GG sees 34.9 squares and 1.68 enemy pieces (16% of the enemy's pieces); its opponent, in the same frame, sees 31.4 squares: a +3.5 advantage that grows through the game (+0.8 in plies 1-20, +2.7 in 21-40, +4.9 after 40). v4: 33.8 squares, 1.53 enemy pieces, advantage +0.3 (-0.4 after ply 40). GG's opponents see 1.35 of its pieces; ours see 1.64 of ours. Yes, it keeps a vision advantage; we do not.

**4. Piece safety.** Value of own pieces on squares attacked by an unseen enemy piece, after the move: GG 1.47 (some piece in 61% of plies, 3+ points in 23%), v4 1.88 (69%, 29%), GG's opponents 1.82, ours 1.67. In plies 21-40: GG 2.02 vs v4 2.72. Own king attacked by an unseen piece after the move: GG 2 plies (0.07%), v4 15 (0.9%), GG's opponents 45 (1.7%).

**5. King exposure** (unseen squares with an open rook or bishop ray to the own king, `exposure()` from hazard.py, after the move): GG 2.05 (rook rays 1.17, bishop 0.88; zero in 55% of plies, 5+ in 19%), v4 2.81 (zero 46%, 5+ in 27%), GG's opponents 2.72, ours 2.35. Opening: 0.32 vs 1.17 (rook rays 0.07 vs 0.92: v4's early e-pawn push and later castling); after ply 40: 3.40 vs 4.52. Against the counterfactual SF top-1 move, both bots pick ~0.2 less exposure than SF would; the gap between GG and v4 comes from the positions they reach (closed d4 openings, early kingside castling, pawns kept in front of the king), not from a stronger per-move preference.

**How the games end.** GG's 54 wins: 35 opponents were in check and moved into/stayed in an attack from an unseen piece, 15 exposed their king to an unseen attacker without being in check, 4 ignored a seen check. GG's 3 losses: Kg2-f2 into an unseen knight while in check with 12.7 s left; Ke7-f8 into an unseen queen while in check (37 s left); Kg1-h1 onto an open h-file with an unseen queen, exposure 18, 16 s left. Think time: GG 5.2 s/move mean (p90 8.2, max 10.2), its opponents 4.2, v4 4.5; GG ends 90 of 179 games with under 20 s on its clock.

**Summary.** Greek Gift is not a better Stockfish imitator than v4; it matches SF top-1 less often and plays a narrower, closed repertoire. What separates it: its non-Stockfish moves are cheap (31 cp vs 42) and lean toward safety (fewer checks, captures and attacked-square moves than SF suggests; never hangs a piece into the fog), it keeps a vision advantage that widens as the game goes on, its king sits with half the open rays ours does, and it escapes seen checks exactly as Stockfish would. We deviate from SF toward attacked squares and king moves, and lose 10 of 19 games to unseen attackers we exposed ourselves to without being in check.

---


Data: random sample (seed 7) of 60 Greek Gift v30 arena games (54 wins, 3 losses, 3 draws; GG white in 36), 2704 GG plies and 2723 opponent plies; and 40 of our v4 arena games (21 wins, 19 losses, 0 draws; v4 white in 23), 1627 v4 plies and 1625 opponent plies.
Engine: Stockfish (bots/eBotI build), depth 8, multipv 3, on the TRUE board before each move. Positions that are not orthodox-legal (the side not to move has its king attacked, or no king) are skipped. 'random' = mean of 1/N and 3/N over the FoW legal move count N. Groups: GG = Greek Gift's moves, GG-opp = its opponents' moves in the same games, v4 = our moves, v4-opp = our opponents' moves.

Opponents of GG in the sample: IAmAVirus (5), Cranberry Lemon (5), Farsight (5), Foggy Fischer (5), Decent Chess Bot (4), Strongly Invisible (4), HYPOTHERMIA (4), TA Baseline S (3), Knight Vision (3), Crimson Fog (3), Lost Signal (2), Cross-Registered Players (2), RATIRL (2), TUM (2), Unicorns (1), Fogbreakers (1), Resting Bishop Faces (1), Next (1), Instructors (1), Fogitos (1), Gravel Road (1), ADARSH (1), Sausage (1), Team 319 (1), duck (1).
Opponents of v4 in the sample: Knight Vision (4), Farsight (4), duck (3), IAmAVirus (3), Resting Bishop Faces (3), Mist Opportunities (3), Greek Gift (3), RATIRL (2), TUM (2), sillygeese (1), baseline.py (1), Gravel Road (1), HYPOTHERMIA (1), TA Baseline P (1), Crimson Fog (1), Lost Signal (1), Bit Gambit (1), Cranberry Lemon (1), Decent Chess Bot (1), Trojan Horse (1), TA Baseline S (1), Cross-Registered Players (1).

## 1. Agreement with true-board Stockfish (depth 8, multipv 3)

| group | plies | SF-scored | top-1 | top-3 | random top-1 / top-3 |
|---|---|---|---|---|---|
| GG | 2704 | 2703 | 33% | 62% | 3% / 10% |
| GG-opp | 2723 | 2705 | 27% | 53% | 4% / 13% |
| v4 | 1627 | 1624 | 37% | 62% | 4% / 12% |
| v4-opp | 1625 | 1617 | 32% | 58% | 4% / 11% |

By phase (plies 1-20, 21-40, 41+):

| phase | GG top-1 / top-3 | GG-opp top-1 / top-3 | v4 top-1 / top-3 | v4-opp top-1 / top-3 |
|---|---|---|---|---|
| 1-20 | 37% / 72% (n=600) | 34% / 64% (n=600) | 50% / 71% (n=400) | 35% / 68% (n=400) |
| 21-40 | 39% / 67% (n=594) | 29% / 55% (n=592) | 40% / 65% (n=380) | 42% / 67% (n=380) |
| 41+ | 29% / 56% (n=1509) | 24% / 47% (n=1513) | 30% / 56% (n=844) | 26% / 49% (n=837) |

Agreement when the mover is in check (own king attacked; Stockfish only considers check escapes, FoW allows anything):

| group | plies in check | SF-scored | top-1 | top-3 |
|---|---|---|---|---|
| GG | 61 | 60 | 75% | 97% |
| GG-opp | 133 | 118 | 51% | 73% |
| v4 | 61 | 59 | 46% | 76% |
| v4-opp | 98 | 91 | 53% | 77% |

When the bot's move is NOT in Stockfish's top 3: the piece moved by the bot vs the piece Stockfish's top-1 would move (share of the disagreeing plies).

| group | disagreeing plies | pawn bot/SF | minor+rook bot/SF | queen bot/SF | king bot/SF | castle bot/SF | bot capture |
|---|---|---|---|---|---|---|---|
| GG | 1026 | 21% / 30% | 52% / 46% | 15% / 14% | 11% / 9% | 1% / 0% | 6% |
| GG-opp | 1281 | 23% / 32% | 48% / 42% | 12% / 12% | 17% / 14% | 0% / 1% | 8% |
| v4 | 619 | 27% / 25% | 45% / 46% | 12% / 19% | 15% / 9% | 1% / 0% | 9% |
| v4-opp | 687 | 24% / 27% | 49% / 46% | 11% / 14% | 14% / 13% | 2% / 1% | 9% |

## 2. Move-type shares

Share of each side's moves. 'check' = the move leaves the enemy king attacked. 'king move' excludes castling. 'dest attacked (any)' = after the move the destination square is attacked by some enemy piece on the true board; 'dest attacked (unseen)' = by an enemy piece whose square is '?' in the mover's view before the move; A destination square is always visible to the mover (FoW vision = squares own pieces can move to), so 'moves into the fog' do not exist.

| group | plies | capture | check | king move | queen move | pawn move | castling | promotion | dest attacked (any) | dest attacked (unseen) |
|---|---|---|---|---|---|---|---|---|---|---|
| GG | 2704 | 22% | 5% | 8% | 13% | 28% | 2% | 1% | 26% | 24% |
| GG-opp | 2723 | 19% | 2% | 17% | 11% | 26% | 2% | 0% | 27% | 25% |
| v4 | 1627 | 23% | 6% | 12% | 11% | 29% | 2% | 1% | 33% | 30% |
| v4-opp | 1625 | 25% | 4% | 12% | 11% | 27% | 2% | 0% | 27% | 25% |

Same by phase:

| group | phase | plies | capture | check | king move | queen move | pawn move | castling | dest attacked (any) | dest attacked (unseen) |
|---|---|---|---|---|---|---|---|---|---|---|
| GG | 1-20 | 600 | 16% | 1% | 0% | 2% | 45% | 6% | 29% | 26% |
| GG | 21-40 | 594 | 30% | 4% | 2% | 15% | 24% | 3% | 32% | 27% |
| GG | 41+ | 1510 | 21% | 7% | 13% | 16% | 23% | 0% | 23% | 21% |
| GG-opp | 1-20 | 600 | 17% | 2% | 1% | 5% | 43% | 5% | 25% | 23% |
| GG-opp | 21-40 | 594 | 25% | 2% | 6% | 12% | 27% | 3% | 38% | 34% |
| GG-opp | 41+ | 1529 | 17% | 3% | 27% | 12% | 19% | 0% | 24% | 23% |
| v4 | 1-20 | 400 | 20% | 3% | 0% | 4% | 44% | 5% | 32% | 30% |
| v4 | 21-40 | 380 | 33% | 6% | 3% | 11% | 25% | 3% | 45% | 41% |
| v4 | 41+ | 847 | 19% | 7% | 22% | 14% | 24% | 0% | 27% | 24% |
| v4-opp | 1-20 | 400 | 23% | 2% | 3% | 11% | 40% | 4% | 29% | 26% |
| v4-opp | 21-40 | 380 | 36% | 2% | 7% | 12% | 24% | 4% | 34% | 31% |
| v4-opp | 41+ | 845 | 20% | 5% | 19% | 10% | 21% | 0% | 24% | 22% |

Castling: share of games in which the side castled, and the mean ply of castling.

| group | games | castled in | mean castling ply | kingside share |
|---|---|---|---|---|
| GG | 60 | 92% | 17.67 | 93% |
| GG-opp | 60 | 73% | 18.18 | 82% |
| v4 | 40 | 80% | 20.00 | 84% |
| v4-opp | 40 | 78% | 21.61 | 74% |

Check moves: share that are also captures, and the checking piece.

| group | check moves | also capture | by queen | by pawn |
|---|---|---|---|---|
| GG | 133 | 41% | 44% | 11% |
| GG-opp | 66 | 53% | 30% | 15% |
| v4 | 99 | 44% | 32% | 10% |
| v4-opp | 61 | 39% | 39% | 7% |

## 3. Vision after each move

'seen squares' = non-'?' squares in the mover's own view after its move (own pieces included). 'enemy pieces seen' = enemy pieces visible, with the enemy's total piece count for reference. 'opp seen (same frame)' = the number of squares the opponent sees in the same frame (i.e. with the opponent to move), and the mover's advantage = seen - opp seen.

| group | plies | seen squares | enemy pieces seen | enemy pieces total | enemy seen share | opp seen (same frame) | advantage (seen - opp) | own pieces the opp sees | own pieces total |
|---|---|---|---|---|---|---|---|---|---|
| GG | 2704 | 34.94 | 1.68 | 10.53 | 16% | 31.42 | 3.52 | 1.35 | 11.17 |
| GG-opp | 2723 | 32.05 | 1.44 | 11.04 | 13% | 34.24 | -2.19 | 1.59 | 10.59 |
| v4 | 1627 | 33.81 | 1.53 | 10.49 | 15% | 33.55 | 0.26 | 1.64 | 10.17 |
| v4-opp | 1625 | 34.27 | 1.70 | 10.05 | 17% | 33.11 | 1.16 | 1.38 | 10.59 |

By phase:

| group | phase | plies | seen squares | enemy pieces seen | enemy seen share | advantage (seen - opp) | own pieces the opp sees |
|---|---|---|---|---|---|---|---|
| GG | 1-20 | 600 | 37.52 | 1.29 | 8% | 0.84 | 1.07 |
| GG | 21-40 | 594 | 39.82 | 2.55 | 20% | 2.70 | 1.93 |
| GG | 41+ | 1510 | 32.00 | 1.50 | 19% | 4.91 | 1.23 |
| GG-opp | 1-20 | 600 | 37.49 | 1.14 | 7% | 0.66 | 1.20 |
| GG-opp | 21-40 | 594 | 38.06 | 2.12 | 16% | -0.73 | 2.41 |
| GG-opp | 41+ | 1529 | 27.59 | 1.29 | 15% | -3.87 | 1.43 |
| v4 | 1-20 | 400 | 37.97 | 0.98 | 7% | 1.12 | 1.50 |
| v4 | 21-40 | 380 | 39.26 | 2.35 | 19% | 0.71 | 2.24 |
| v4 | 41+ | 847 | 29.39 | 1.43 | 19% | -0.36 | 1.43 |
| v4-opp | 1-20 | 400 | 37.85 | 1.66 | 11% | 0.66 | 0.87 |
| v4-opp | 21-40 | 380 | 39.51 | 2.27 | 19% | 1.49 | 1.97 |
| v4-opp | 41+ | 845 | 30.22 | 1.47 | 21% | 1.25 | 1.35 |

## 4. Piece safety after each move

After the mover's move, on the true board: value (P1 N3 B3 R5 Q9, king excluded) of the mover's pieces standing on a square attacked by an enemy piece whose square is '?' in the mover's view after the move ('unseen-attacked'); the count of such pieces; the share of plies with at least one; value attacked by ANY enemy piece (seen or not) for reference; and the share of plies after which the mover's own king is attacked by an unseen piece (that is the losing condition when the game ends; the last ply of a lost game is included).

| group | plies | unseen-attacked value | unseen-attacked pieces | plies with any | plies with >=3 value | attacked value (any) | own material | king attacked by unseen | count |
|---|---|---|---|---|---|---|---|---|---|
| GG | 2704 | 1.47 | 1.00 | 61% | 23% | 2.28 | 25.51 | 0% | 2 |
| GG-opp | 2723 | 1.82 | 1.22 | 70% | 28% | 2.60 | 23.78 | 2% | 45 |
| v4 | 1627 | 1.88 | 1.23 | 69% | 29% | 2.86 | 23.47 | 1% | 15 |
| v4-opp | 1625 | 1.67 | 1.03 | 62% | 26% | 2.44 | 24.04 | 1% | 15 |

By phase:

| group | phase | plies | unseen-attacked value | plies with any | attacked value (any) | king attacked by unseen |
|---|---|---|---|---|---|---|
| GG | 1-20 | 600 | 1.07 | 51% | 1.55 | 0% |
| GG | 21-40 | 594 | 2.02 | 77% | 3.21 | 0% |
| GG | 41+ | 1510 | 1.40 | 58% | 2.20 | 0% |
| GG-opp | 1-20 | 600 | 1.30 | 62% | 1.81 | 0% |
| GG-opp | 21-40 | 594 | 2.98 | 88% | 4.14 | 1% |
| GG-opp | 41+ | 1529 | 1.57 | 66% | 2.31 | 3% |
| v4 | 1-20 | 400 | 1.68 | 70% | 2.26 | 0% |
| v4 | 21-40 | 380 | 2.72 | 85% | 4.28 | 0% |
| v4 | 41+ | 847 | 1.61 | 61% | 2.50 | 2% |
| v4-opp | 1-20 | 400 | 0.91 | 43% | 1.51 | 0% |
| v4-opp | 21-40 | 380 | 2.42 | 78% | 3.58 | 1% |
| v4-opp | 41+ | 845 | 1.70 | 64% | 2.36 | 1% |

## 5. King exposure after each move

exposure(view, king) from bots/eBotI/eBotI/hazard.py on the mover's view after its move: unseen squares on the king's ranks/files (rook rays) and diagonals (bishop rays), each ray stopping at the first seen piece; knight squares unseen for reference.

| group | plies | rook rays | bishop rays | rook+bishop | median | share = 0 | share >= 5 | share >= 10 | knight squares |
|---|---|---|---|---|---|---|---|---|---|
| GG | 2704 | 1.17 | 0.88 | 2.05 | 0 | 55% | 19% | 4% | 0.95 |
| GG-opp | 2723 | 1.65 | 1.08 | 2.72 | 0 | 51% | 26% | 9% | 0.99 |
| v4 | 1627 | 1.81 | 1.00 | 2.81 | 1 | 46% | 27% | 8% | 1.04 |
| v4-opp | 1625 | 1.41 | 0.94 | 2.35 | 1 | 48% | 22% | 6% | 1.10 |

By phase:

| group | phase | plies | rook rays | bishop rays | rook+bishop | share = 0 | share >= 5 |
|---|---|---|---|---|---|---|---|
| GG | 1-20 | 600 | 0.07 | 0.24 | 0.32 | 75% | 0% |
| GG | 21-40 | 594 | 0.14 | 0.23 | 0.37 | 82% | 1% |
| GG | 41+ | 1510 | 2.02 | 1.38 | 3.40 | 37% | 33% |
| GG-opp | 1-20 | 600 | 0.35 | 0.24 | 0.59 | 68% | 4% |
| GG-opp | 21-40 | 594 | 0.33 | 0.24 | 0.57 | 75% | 3% |
| GG-opp | 41+ | 1529 | 2.67 | 1.73 | 4.40 | 34% | 44% |
| v4 | 1-20 | 400 | 0.92 | 0.25 | 1.17 | 56% | 11% |
| v4 | 21-40 | 380 | 0.47 | 0.23 | 0.71 | 73% | 6% |
| v4 | 41+ | 847 | 2.83 | 1.69 | 4.52 | 29% | 45% |
| v4-opp | 1-20 | 400 | 0.31 | 0.32 | 0.63 | 62% | 4% |
| v4-opp | 21-40 | 380 | 0.57 | 0.35 | 0.92 | 69% | 7% |
| v4-opp | 41+ | 845 | 2.30 | 1.50 | 3.80 | 32% | 36% |

Did the bot choose lower exposure than Stockfish would? For plies where the bot's move differs from SF top-1, exposure after the bot's move vs after SF's top-1 move (applied to the true board, viewed with the mover's observation recomputed from the true board).

| group | plies (bot != SF top-1) | exposure after bot move | exposure after SF top-1 | unseen-attacked value after bot move | after SF top-1 |
|---|---|---|---|---|---|
| GG | 1820 | 2.13 | 2.29 | 1.43 | 1.43 |
| GG-opp | 1972 | 2.77 | 3.01 | 1.86 | 1.75 |
| v4 | 1019 | 3.00 | 3.20 | 1.99 | 1.82 |
| v4-opp | 1103 | 2.48 | 2.71 | 1.63 | 1.58 |

## 6. How far from Stockfish, and in which direction

True-board centipawn loss: Stockfish depth-8 eval (mover's point of view, mate = +-1000) of the position after the bot's move minus the eval after Stockfish's top-1 move. Plies where either move ends the game (king capture, or the mover leaves its own king attackable) are skipped. A negative loss means the bot's move evaluates better than SF's top-1 at this shallow depth.

| group | plies | mean loss (cp) | median | loss <= 0 | > 50 | > 100 | > 300 | > 600 |
|---|---|---|---|---|---|---|---|---|
| GG | 2701 | 31 | 0 | 56% | 22% | 13% | 2% | 0% |
| GG-opp | 2669 | 44 | 3 | 48% | 27% | 16% | 4% | 1% |
| v4 | 1608 | 42 | 0 | 57% | 24% | 14% | 3% | 1% |
| v4-opp | 1604 | 43 | 0 | 52% | 26% | 15% | 4% | 1% |

By phase:

| group | phase | plies | mean loss (cp) | median | > 100 | > 300 |
|---|---|---|---|---|---|---|
| GG | 1-20 | 600 | 14 | 0 | 4% | 0% |
| GG | 21-40 | 594 | 34 | 0 | 15% | 2% |
| GG | 41+ | 1507 | 37 | 0 | 16% | 3% |
| GG-opp | 1-20 | 600 | 28 | 6 | 7% | 2% |
| GG-opp | 21-40 | 589 | 59 | 8 | 19% | 6% |
| GG-opp | 41+ | 1480 | 45 | 1 | 18% | 4% |
| v4 | 1-20 | 400 | 29 | 0 | 7% | 2% |
| v4 | 21-40 | 380 | 52 | 0 | 19% | 5% |
| v4 | 41+ | 828 | 43 | 0 | 15% | 3% |
| v4-opp | 1-20 | 399 | 34 | 0 | 11% | 3% |
| v4-opp | 21-40 | 378 | 38 | 0 | 16% | 4% |
| v4-opp | 41+ | 827 | 50 | 2 | 18% | 4% |

Style delta against Stockfish: on plies where the bot's move differs from SF top-1, properties of the bot's move vs the SF move (both applied to the true board; the view after the SF move is recomputed from the true board). Vision = squares seen / enemy pieces seen after the move.

| group | plies (bot != SF top-1) | capture bot/SF | check bot/SF | king move bot/SF | queen move bot/SF | pawn move bot/SF | dest attacked bot/SF | seen squares bot/SF | enemy pieces seen bot/SF | king exposure bot/SF | unseen-attacked value bot/SF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GG | 1820 | 12% / 16% | 3% / 6% | 11% / 8% | 13% / 13% | 26% / 31% | 21% / 29% | 34.36 / 34.71 | 1.58 / 1.74 | 2.13 / 2.29 | 1.43 / 1.43 |
| GG-opp | 1972 | 11% / 12% | 2% / 2% | 19% / 14% | 11% / 12% | 24% / 33% | 25% / 30% | 31.69 / 31.92 | 1.42 / 1.52 | 2.77 / 3.01 | 1.86 / 1.75 |
| v4 | 1019 | 13% / 17% | 4% / 8% | 17% / 11% | 11% / 19% | 27% / 25% | 31% / 25% | 33.05 / 33.20 | 1.49 / 1.54 | 3.00 / 3.20 | 1.99 / 1.82 |
| v4-opp | 1103 | 14% / 14% | 3% / 5% | 16% / 12% | 11% / 12% | 26% / 27% | 24% / 26% | 33.56 / 33.63 | 1.62 / 1.60 | 2.48 / 2.71 | 1.63 / 1.58 |

Moves to a square attacked by an unseen enemy piece, broken down: piece moved and whether the destination is defended by the mover (a pawn or a defended piece on an attacked square is usually a trade offer; an undefended non-pawn on an attacked square is a piece hung into the fog). Shares of ALL the group's moves.

| group | plies | pawn to unseen-attacked square | defended piece to unseen-attacked square | undefended non-pawn to unseen-attacked square | count |
|---|---|---|---|---|---|
| GG | 2704 | 11% | 8% | 4% | 115 |
| GG-opp | 2723 | 11% | 8% | 5% | 148 |
| v4 | 1627 | 13% | 10% | 7% | 106 |
| v4-opp | 1625 | 12% | 8% | 5% | 76 |

The same, captures and king moves separated (shares of all the group's moves): a capture onto an unseen-attacked square is a trade offer; a king move onto an attacked square ends the game.

| group | plies | capture | quiet pawn | quiet defended piece | quiet undefended piece (hung) | hung count | king onto attacked square |
|---|---|---|---|---|---|---|---|
| GG | 2704 | 11% | 7% | 5% | 0% | 4 | 2 |
| GG-opp | 2723 | 11% | 8% | 6% | 1% | 14 | 17 |
| v4 | 1627 | 12% | 9% | 7% | 1% | 16 | 11 |
| v4-opp | 1625 | 11% | 8% | 5% | 1% | 12 | 9 |

## 7. Being in check, and how the games end

In check = the mover's king is attacked before its move. Split by whether the attacker is visible in the mover's view (recomputed from the true board). Agreement with SF top-1/top-3 on those plies; 'king still attacked' = the mover's move left its king attackable (game over, lost).

| group | attacker | plies in check | SF-scored | top-1 | top-3 | king still attacked after (lost) |
|---|---|---|---|---|---|---|
| GG | seen | 46 | 45 | 84% | 100% | 1 |
| GG | unseen | 15 | 15 | 47% | 87% | 1 |
| GG-opp | seen | 63 | 54 | 70% | 91% | 12 |
| GG-opp | unseen | 70 | 64 | 34% | 58% | 27 |
| v4 | seen | 23 | 23 | 70% | 91% | 2 |
| v4 | unseen | 38 | 36 | 31% | 67% | 7 |
| v4-opp | seen | 57 | 52 | 60% | 85% | 9 |
| v4-opp | unseen | 41 | 39 | 44% | 67% | 7 |

Game-ending plies (the mover's own king attackable after its move), split by whether the mover was in check before the move and whether the piece attacking the king AFTER the move was visible in the mover's pre-move view. 'seen' = the bot moved into or stayed in an attack it could see (a blunder); 'unseen' = the attacker was in the fog. Games lost on time or drawn have no such ply.

| group | lost plies | in check, final attacker seen | in check, final attacker unseen | not in check, attacker seen | not in check, attacker unseen |
|---|---|---|---|---|---|
| GG | 3 | 0 | 2 | 0 | 1 |
| GG-opp | 54 | 4 | 35 | 0 | 15 |
| v4 | 19 | 0 | 9 | 0 | 10 |
| v4-opp | 21 | 4 | 12 | 0 | 5 |

## Appendix: Greek Gift per game

| game | GG side | opponent | result | GG plies | GG top-1 | GG top-3 | opp top-1 | opp top-3 | GG seen sq | GG exposure | GG unseen-attacked value |
|---|---|---|---|---|---|---|---|---|---|---|---|
| toqmp7ys | W | IAmAVirus | win | 47 | 28% | 60% | 24% | 41% | 38.62 | 0.13 | 1.94 |
| d42u2qjh | B | IAmAVirus | win | 50 | 28% | 64% | 24% | 49% | 31.10 | 4.12 | 0.84 |
| adcvfumo | W | Cranberry Lemon | win | 71 | 37% | 63% | 34% | 57% | 32.18 | 4.13 | 0.97 |
| 8o58b0xu | B | Unicorns | win | 36 | 39% | 61% | 25% | 44% | 39.89 | 0.03 | 1.39 |
| 723mkkbl | W | Lost Signal | win | 74 | 24% | 62% | 20% | 46% | 29.64 | 3.89 | 1.32 |
| jk2b9wwa | B | Farsight | win | 50 | 46% | 70% | 25% | 61% | 34.64 | 0.96 | 0.84 |
| i4koxbx9 | W | Decent Chess Bot | win | 25 | 36% | 68% | 16% | 48% | 41.40 | 0.40 | 1.32 |
| iyiyd3a8 | W | TA Baseline S | win | 18 | 33% | 72% | 39% | 61% | 42.22 | 0.06 | 0.39 |
| r340htvx | B | Strongly Invisible | draw | 44 | 36% | 70% | 32% | 50% | 34.16 | 1.98 | 1.18 |
| 22ugtqln | W | TA Baseline S | win | 50 | 24% | 50% | 24% | 50% | 34.70 | 2.44 | 1.20 |
| cmpp8ys6 | B | Knight Vision | win | 23 | 30% | 65% | 42% | 54% | 38.87 | 0.04 | 1.74 |
| 3t6vsx3q | B | Fogbreakers | win | 81 | 16% | 43% | 9% | 30% | 32.60 | 2.19 | 0.59 |
| u6s7qu6m | B | Cross-Registered Players | win | 84 | 29% | 49% | 22% | 45% | 32.13 | 1.94 | 2.21 |
| m6750mh5 | W | Farsight | win | 58 | 26% | 55% | 29% | 59% | 32.05 | 3.81 | 1.40 |
| dvw8bxr3 | W | HYPOTHERMIA | win | 57 | 26% | 67% | 23% | 47% | 35.98 | 2.35 | 1.07 |
| 0fk2j5gy | W | Resting Bishop Faces | win | 20 | 55% | 80% | 42% | 74% | 45.60 | 0.10 | 1.25 |
| pm3e1zaq | B | RATIRL | draw | 31 | 39% | 84% | 31% | 66% | 34.84 | 1.68 | 2.26 |
| fxq0ef6o | W | Cranberry Lemon | win | 50 | 42% | 70% | 18% | 58% | 36.30 | 1.56 | 1.94 |
| ae2yfkb5 | W | Next | draw | 88 | 31% | 58% | 24% | 55% | 30.83 | 2.97 | 1.48 |
| 5yc8e4xr | B | Instructors | win | 60 | 28% | 72% | 26% | 48% | 31.72 | 2.62 | 1.13 |
| q38lr2gg | B | Lost Signal | win | 75 | 31% | 53% | 21% | 38% | 32.52 | 0.84 | 1.99 |
| m3441wsf | W | IAmAVirus | win | 33 | 33% | 64% | 33% | 58% | 38.33 | 1.79 | 0.88 |
| ft59z06p | B | Decent Chess Bot | win | 64 | 27% | 53% | 32% | 52% | 34.73 | 1.59 | 2.28 |
| wtlwy1lc | B | TUM | win | 61 | 34% | 66% | 31% | 48% | 34.66 | 2.54 | 1.39 |
| 1sw9k66h | W | Fogitos | win | 21 | 38% | 76% | 24% | 33% | 43.00 | 0.24 | 1.05 |
| 70i3cc0s | B | IAmAVirus | win | 28 | 50% | 89% | 24% | 55% | 38.46 | 2.50 | 1.18 |
| d6iwp3pn | W | Farsight | win | 29 | 41% | 76% | 48% | 66% | 39.55 | 2.07 | 0.90 |
| mrctmykd | B | Foggy Fischer | win | 39 | 31% | 67% | 18% | 58% | 34.85 | 1.00 | 1.79 |
| 7pijihc6 | W | TUM | win | 32 | 34% | 59% | 13% | 32% | 39.88 | 0.31 | 1.25 |
| pdi24olq | W | Foggy Fischer | win | 30 | 37% | 67% | 21% | 59% | 41.83 | 0.33 | 1.70 |
| 8peth99v | W | Strongly Invisible | win | 51 | 31% | 51% | 39% | 57% | 35.02 | 3.29 | 1.20 |
| k1uhkbuq | W | TA Baseline S | win | 49 | 33% | 57% | 31% | 48% | 33.47 | 2.12 | 0.67 |
| 0askyt3o | B | Crimson Fog | win | 45 | 20% | 49% | 13% | 40% | 38.47 | 0.49 | 0.84 |
| ysrf7il4 | W | IAmAVirus | win | 19 | 53% | 79% | 50% | 72% | 39.53 | 1.11 | 0.42 |
| zwkhppqp | W | Strongly Invisible | LOSS | 55 | 24% | 50% | 28% | 48% | 29.44 | 2.84 | 2.44 |
| l3qqr2x9 | B | Gravel Road | win | 37 | 32% | 65% | 21% | 68% | 36.97 | 1.89 | 1.70 |
| enti5chy | W | Farsight | win | 24 | 33% | 75% | 52% | 78% | 40.67 | 0.04 | 1.38 |
| y9sa8t4u | B | Cranberry Lemon | win | 42 | 40% | 71% | 37% | 58% | 35.52 | 1.19 | 1.31 |
| hk5xnaw6 | B | Crimson Fog | LOSS | 35 | 31% | 60% | 40% | 71% | 34.49 | 0.97 | 4.06 |
| ckvmtjj1 | W | Cross-Registered Players | win | 18 | 44% | 83% | 17% | 44% | 40.83 | 0.50 | 1.78 |
| pyvufwbh | W | HYPOTHERMIA | win | 34 | 59% | 88% | 48% | 73% | 40.24 | 1.38 | 0.71 |
| xn0i0st0 | B | ADARSH | win | 59 | 22% | 46% | 5% | 39% | 37.05 | 0.14 | 1.31 |
| qd3gpp7d | W | Decent Chess Bot | win | 46 | 30% | 65% | 20% | 39% | 37.98 | 0.46 | 2.24 |
| dafzcwl7 | W | Foggy Fischer | win | 29 | 55% | 83% | 52% | 69% | 40.59 | 1.41 | 1.62 |
| qbo1yj47 | W | Sausage | win | 22 | 32% | 59% | 10% | 52% | 38.68 | 0.41 | 1.05 |
| 50h61idz | W | Team 319 | win | 28 | 50% | 71% | 44% | 74% | 39.61 | 0.61 | 2.04 |
| euso5qlc | W | Crimson Fog | win | 28 | 29% | 57% | 29% | 46% | 36.46 | 1.36 | 0.86 |
| ww2ykpkn | W | duck | LOSS | 41 | 20% | 59% | 38% | 65% | 37.15 | 1.59 | 2.83 |
| 77n86jwg | W | Strongly Invisible | win | 33 | 33% | 67% | 27% | 58% | 39.39 | 1.00 | 3.85 |
| zaguz1ig | B | Cranberry Lemon | win | 48 | 44% | 69% | 22% | 51% | 27.73 | 5.46 | 1.69 |
| 5voxnm4s | B | Decent Chess Bot | win | 89 | 30% | 60% | 22% | 43% | 30.79 | 2.97 | 1.35 |
| lbofkt5y | W | Foggy Fischer | win | 68 | 44% | 76% | 39% | 69% | 34.12 | 4.41 | 0.90 |
| hupeig41 | W | Knight Vision | win | 29 | 34% | 72% | 25% | 54% | 38.41 | 0.10 | 1.41 |
| ldwyip4h | B | Cranberry Lemon | win | 86 | 22% | 49% | 27% | 50% | 33.44 | 3.34 | 1.52 |
| an8d2x1u | W | HYPOTHERMIA | win | 45 | 47% | 71% | 24% | 60% | 32.47 | 2.40 | 2.13 |
| 4tpo2k9i | B | RATIRL | win | 30 | 53% | 77% | 26% | 68% | 35.53 | 2.10 | 2.20 |
| m9ajv66u | W | Knight Vision | win | 19 | 42% | 68% | 26% | 42% | 40.74 | 0.11 | 1.47 |
| 9noy6mzf | W | HYPOTHERMIA | win | 87 | 21% | 38% | 29% | 61% | 30.06 | 4.70 | 0.51 |
| fs6589vu | W | Farsight | win | 35 | 46% | 77% | 43% | 77% | 37.91 | 1.31 | 0.83 |
| z0aig98o | B | Foggy Fischer | win | 44 | 30% | 61% | 32% | 41% | 36.39 | 0.11 | 1.55 |
