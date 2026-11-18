# Greek Gift (v30) versus Magnus Monte Carlsen (v4): openings, early endings, vision

Data: 179 arena games of Greek Gift v30 (`gg_games.pkl`), 150 arena games of our v4
(`replays_cache.pkl`). Time control 180+2 in both. Six games are head-to-head and appear in
both sets (GG won all six: plies 144, 149, 60, 49, 103, 44).
Scripts and raw output: `analyze.py` / `analysis_output.txt` (trees, determinism, early
endings, vision, time), `analyze2.py` / `analysis2_output.txt` (black trees, ending
mechanics, material, checks, common opponents), `analyze3.py` / `analysis3_output.txt`
(en prise, queen losses, walked-in losses, time by phase, king exposure), `analyze4.py`.

Rules reminder (starter/referee.py): the outcome is checked at the start of each turn, so a
game ends on the move that leaves the mover's own king attackable; the king is never
actually captured. "Check" below means the king is attacked with full information; the
victim usually cannot see the attacker.

| | games | W | D | L | score | reasons |
|---|---|---|---|---|---|---|
| Greek Gift as white | 90 | 85 | 1 | 4 | 0.95 | King capturable 174, threefold 5 (all games) |
| Greek Gift as black | 89 | 78 | 4 | 7 | 0.90 | |
| Ours v4 as white | 75 | 44 | 1 | 30 | 0.59 | King capturable 145, threefold 3, time forfeit 1, 50-move 1 |
| Ours v4 as black | 75 | 38 | 3 | 34 | 0.53 | |

Over the 25 opponents both bots have played (weighted by min games per opponent, weight 100):
Greek Gift scores 0.93, we score 0.52. Examples: Strongly Invisible GG 0.86 (14 games) vs
ours 0.17 (6); IAmAVirus 1.00 (10) vs 0.33 (6); duck 0.75 (8) vs 0.40 (10); Resting Bishop
Faces 1.00 (6) vs 0.59 (16); Gravel Road 0.88 (8) vs 0.00 (4). The gap is not an opponent
mix effect.

## 1. Greek Gift's opening repertoire

### As white (90 games): always 1.d4, then a Queen's-pawn system

First six own moves, most common sequences (ignoring the opponent):

| n | GG's moves 1-6 |
|---|---|
| 11 | d4 c4 cxd5 Bf4 e3 Nc3 |
| 6 | d4 c4 cxd5 Nc3 Bf4 e3 |
| 5 | d4 Nc3 e4 f3 fxe4 Bc4 (vs 1...f5: Staunton-style gambit) |
| 3 | d4 Nc3 e4 e5 f4 Nf3 (vs 1...Nf6 2...e6 3...d5) |
| 2 each | d4 Bf4 e3 Nf3 Bd3 Nd2; d4 c4 cxd5 Bf4 Nc3 e3; d4 d5 Nc3 a4 e4 h4; d4 Bf4 e3 Nd2 Bd3 h3; d4 Nc3 Bf4 e3 Bd3 Nf3 |

64 distinct 6-move sequences in 90 games. Per move number: move 1 d4 90/90; move 2 Nc3 31,
c4 24, Bf4 21, d5 13, e4 1; move 3 cxd5 22, e4 19, e3 16, Nc3 14, Bf4 10; move 4 Bf4 15, e3 12,
e4 8, Nf3 8, Nc3 8, f3 6; move 5 Bd3 18, e3 13, Nf3 8, Bf4 7; move 6 Nc3 12, e3 9, Nf3 8, Bc4 6.

Tree conditioned on the opponent's replies (nodes with >= 2 games; full tree in
`analysis_output.txt`):

```
1.d4 (90/90)
  1...d5 (44): 2.c4 23/44 | 2.Bf4 21/44
      2.c4 e6 (15): 3.cxd5 15/15 exd5 4.Bf4 15/15 c6 (11) 5.e3 9/11 (5.Nc3 2) Be7 (7) 6.Nc3 7/7
      2.c4 c6 (7):  3.cxd5 6/7, then 4.Nc3, 5.Bf4, 6.e3
      2.Bf4 ... (Nf6/e6/Bf5/c6): 3.e3 (every time), later Nf3/Nd2/Bd3
  1...c5 (13): 2.d5 13/13, 3.Nc3 (always seen), 4.a4 / 4.e4
  1...Nf6 (9): 2.Nc3 9/9; ...e6 3.e4 6/6; ...d5 4.e5 3/4 Nfd7 5.f4 c5 6.Nf3
  1...f5 (7):  2.Nc3 6/7 Nf6 3.e4 5/5 fxe4 4.f3 5/5 d5 5.fxe4 5/5 dxe4 6.Bc4 5/5
  1...Nc6 (7): 2.Nc3 7/7; ...d5 3.Bf4; ...Nf6 3.e4
  1...c6 (7):  2.Nc3 6/7 d5 3.Bf4 5/5 Nf6 4.e3 4/4
  1...e6 (3):  2.Nc3 3/3
```

Most common full 10-ply sequences (75 distinct in 90 games):

| n | plies 1-10 |
|---|---|
| 7 | d4 d5 c4 e6 cxd5 exd5 Bf4 c6 e3 Be7 |
| 5 | d4 f5 Nc3 Nf6 e4 fxe4 f3 d5 fxe4 dxe4 |
| 3 | d4 Nf6 Nc3 e6 e4 d5 e5 Nfd7 f4 c5 |
| 2 | d4 c6 Nc3 d5 Bf4 Nf6 e3 e6 Bd3 Bd6 |
| 2 | d4 d5 c4 e6 cxd5 exd5 Bf4 c6 e3 Nf6 |
| 2 | d4 d5 c4 c6 cxd5 Bd7 Nc3 cxd5 Bf4 e6 |

Character: an Exchange QGD / London hybrid. The c-pawn exchanges on d5 at once
(cxd5 22/22 after 2.c4 d5), the bishop goes to f4 before e3 closes it in, knights to c3 and
f3/e2, bishop to d3, short castle. No early queen move (queen first moves at median ply 26;
only 3% of GG's first-20-ply moves are queen moves). No f7 raids, no Bxh7 sacrifice; the
name is not descriptive of its play.

### As black (89 games): Slav/Caro (...c6 ...d5) or King's Indian / Grunfeld setups (...Nf6 ...g6 ...Bg7 O-O)

| n | GG's moves 1-6 |
|---|---|
| 7 | c6 d5 cxd5 Nc6 Bf5 e6 |
| 7 | c6 d5 Nf6 g6 Bg7 O-O |
| 6 | c6 d5 g6 Nf6 Bg7 O-O |
| 3 each | Nf6 g6 Bg7 O-O d6 Nc6; Nf6 g6 Nc6 d6 Bg7 O-O; Nf6 g6 Bg7 O-O d5 dxc4; c5 g6 Bg7 Nf6 d6 O-O |
| 2 each | c6 d5 cxd5 Nc6 e6 Bd6; c6 d5 g6 Bg7 Nf6 O-O; Nf6 g6 Bg7 O-O d5 Nxd5; c6 d5 Nf6 cxd5 Nc6 e6; Nf6 Ne4 Nf6 g6 Bg7 O-O |

55 distinct sequences in 89 games. Move 1: c6 47, Nf6 32, c5 3, e6 2, g6 2, Nc6 2.
Move 2: d5 49, g6 24, c5 6. Move 6: O-O 31, e6 14, Nc6 8, Nbd7 5.

```
1.d4 (61 games): 1...c6 28 | 1...Nf6 23 | 1...c5 3 | e6/g6/Nc6 2 each
   1.d4 c6 2.c4 d5 (12/12) 3.cxd5 cxd5 9/10 4.Bf4/Nc3 Nc6 4/4 ... Bf5, e6
   1.d4 c6 2.Nc3 d5 (9/9) 3.Bf4 g6 5/7 (Nf6 2/7), then Nf6/g6, Bg7
   1.d4 Nf6 2.c4 g6 6/8 3.Nc3 Bg7 6/6 4.Nf3 O-O 6/6 then ...d6 or ...d5
   1.d4 Nf6 2.Nc3 g6 6/7 3.e4 Nc6 3/6 | Bg7 2/6
   1.d4 c5 2.d5 g6 3/3 3.Nc3 Bg7 3/3
1.e4 (13 games): 1...c6 8 (2.d4 d5 4/4, 3.e5 Bf5 3/3) | 1...Nf6 5 (2.d4 c5 2/3)
1.Nc3 (6): c6 3, Nf6 3.   1.Nf3 (4): c6 4/4.   1.c4 (4): c6 3/4.
```

Most common full 10-ply sequences as black (78 distinct in 89 games): 4x `d4 c6 c4 d5 cxd5
cxd5 Bf4 Nc6 Nc3 Bf5`, 3x `d4 c6 c4 d5 cxd5 cxd5 Nc3 Nc6 Bf4 Bf5`, 3x `d4 Nf6 c4 g6 Nc3 Bg7
Nf3 O-O e4 d6`.

### Determinism

Key = GG's sequence of observations (the view it received before each of its moves) plus its
own previous moves, over its first 10 moves. Among observation-histories seen at least
twice:

| | distinct histories | seen >= 2 times | ...with different moves |
|---|---|---|---|
| GG as white | 495 | 67 | 21 (31%) |
| GG as black | 517 | 83 | 17 (20%) |
| Ours v4 as white | 361 | 59 | 17 (29%) |
| Ours v4 as black | 409 | 72 | 26 (36%) |

GG is not deterministic. The split is sometimes near 50/50 on identical input: after
1.d4 d5 it plays 2.c4 23 times and 2.Bf4 21 times; as black on the empty first observation it
plays 1...c6 47, 1...Nf6 32, c5 3, e6 2, g6 2, Nc6 2, d5 1. Other splits: 2.Nc3 31 / e4 1 / c4 1
after 1.d4 Nf6-type replies; 3...cxd5 12 / Nf6 4 / Bd7 1 / Bf5 1. The variation looks like a
small weighted book or a randomized/anytime search, not a hash-seeded bug: the sequences
are all sane mainstream lines.

GG's clock use is deterministic at the start: it spends 6.21 +/- 0.02 s on move 1 and 6.19
+/- 0.02 s on move 2 in all 179 games, so it is searching (not playing from a book instantly)
with a fixed time budget. Our v4 spends 1.0 s on move 1 as white and 7.5 s as black, in all
games.

## 2. Early endings: Greek Gift never wins early

| | GG (179) | Ours v4 (150) |
|---|---|---|
| shortest game (plies) | 34 | 9 |
| median / mean plies | 86 / 91.0 | 71 / 78.2 |
| ended before ply 20 | 0 | 2 (both our losses) |
| ended before ply 30 | 0 | 9 (7 wins, 2 losses) |
| ended before ply 40 | 8 (7 wins, 1 loss) | 14 (12 wins, 2 losses) |
| ended before ply 60 | 40 (38 wins, 2 losses) | 47 (31 wins, 16 losses) |

GG has no queen/bishop raid phase. Its 7 wins before ply 40 are against Farsight, Lost
Signal, Crimson Fog and similar, all by ordinary attacks after 34-39 plies. Our 9 games under
30 plies: 2 losses as white by walking into an invisible ...Qa5 attacking e1 (plies 9 and 17,
vs Strongly Invisible and TA Baseline A), 7 wins by Q/B/N/R attacks on an uncastled enemy
king on e8/e1 (Bf7, Qh8, Qe5, Qh1, Nc7, Qe4, Re1) against weak bots (Bit Gambit x2, baseline.py,
TA Baseline P, Tiger, Trojan Horse, Mu1tip13).

How the games actually end ("King capturable" only). "Check before" = the loser's king was
already attacked before its final move (the winner had delivered a check the loser could not
see and the loser failed to escape); otherwise the loser walked its king (or uncovered it)
into an unseen attacker.

| | GG wins (163) | GG losses (11) | our wins (81) | our losses (64) |
|---|---|---|---|---|
| check before final move | 104 (64%) | 7 (64%) | 58 (72%) | 26 (41%) |
| ...of which loser had no safe move at all (real mate) | 44 | 3 | 32 | 6 |
| loser moved king while in check | 44 | 4 | 30 | 12 |
| loser moved another piece while in check | 60 | 3 | 28 | 14 |
| **loser walked king into unseen attack (not in check)** | 56 | 3 | 22 | **35** |
| loser uncovered own king with another piece | 3 | 1 | 1 | 3 |
| attacker visible to loser before its move | 7 | 0 | 10 | 1 |
| attacking piece | Q 66, R 64, N 13, B 10, K 10, P 3 | Q 5, R 4, N 2 | Q 38, R 29, B 11, N 6, K 1 | Q 28, R 19, B 6, K 5, N 4, P 2 |
| winner's material lead at the end (mean) | +6.9 | +10.6 (opp lead) | +7.0 | +7.4 (opp lead) |
| mean plies | 90 | 95 | 75 | 77 |

Most frequent attacker squares in GG's wins: Qh8 6, Ra1 5, Re8 5, Qg7 4, Qf1 4, Re2 4, Rg1 3,
Qh5 3; losing king squares h8 11, g1 9, g7 9, g8 8, h7 7, h1 6. GG kills kings on the castled
side, late, with the heavy pieces, after winning material: in 112 of its 163 wins it was
at least 5 points up at the end.

The single largest difference in catastrophes: 35 of our 64 losses (55%) are our king
stepping onto a square attacked by a piece we could not see, with no check pending. GG does
this 3 times in 179 games. In 33 of our 35 cases the attacker had never been seen on that
square by us; in 20 of them it had arrived there within the previous 2 plies (fresh,
unknowable), but in the other 15 it had been sitting there for 4 to 55 plies. Full list in
`analysis3_output.txt` section (c). Typical pattern: king on g1/h2/g7 steps along a file or
diagonal that an enemy queen or rook has been occupying for several moves (e.g. Kg1-h2 with
black queen on e5 or h4; Kg7-h6 with white queen on h2; Kc2-d3 with a rook on d7).

Checks delivered (full information) during the whole game:

| | checks / own moves | attacker fully unseen by victim | victim escaped |
|---|---|---|---|
| GG | 399 / 8110 (4.9%) | 217 (54%) | 295 (74%) |
| GG's opponents (on GG) | 172 / 8185 (2.1%) | 45 (26%) | GG escaped 152 (88%) |
| Ours | 329 / 5858 (5.6%) | 130 (40%) | 265 (81%) |
| our opponents (on us) | 212 / 5865 (3.6%) | 103 (49%) | we escaped 184 (87%) |

GG gets checked 40% less often than we do and its checks are more often invisible to the
victim. Its escape rate when checked is the same as ours.

## 3. Our v4's openings and early outcomes

### As white (75 games): always 1.e4

| n | our moves 1-6 |
|---|---|
| 20 | e4 exd5 Nc3 Be2 Nf3 d4 (vs 1...d5 2...Qxd5 3...Qd8) |
| 5 | e4 d4 Nc3 dxe5 Qxd8 Nf3 (vs 1...Nf6 2...d6 3...e5: queen trade on d8) |
| 4 | e4 d4 Nc3 dxe5 Qxd8 Bc4 |
| 3 | e4 exd5 dxc6 Nf3 Nc3 Bb5 |
| 2 each | e4 d4 Nc3 e5 Nxe4 c3; e4 exf5 d4 Bd3 Nf3 O-O |

45 distinct in 75 games. Move 2: d4 39, exd5 32, exf5 3, Nf3 1. Move 3: Nc3 37, exd5 11, d4 8,
Nf3 5. Tree:

```
1.e4 (75/75)
  1...d5 (32): 2.exd5 32/32 Qxd5 (24) 3.Nc3 20/24 (3.d4 2, 3.Nf3 2) Qd8/Qe6/Qd6 4.Be2 (always) 5.Nf3 6.d4
             2...c6 (4): 3.dxc6 4/4 Nxc6 4.Nf3 4/4 e5 5.Nc3 Bc5 6.Bb5
  1...Nf6 (18): 2.d4 18/18 d6 (10) 3.Nc3 10/10 e5 (9) 4.dxe5 9/9 dxe5 5.Qxd8+ 9/9 Kxd8 6.Nf3 5 / Bc4 4
  1...c6 (9):  2.d4 9/9 d5 (8) 3.exd5 7/8
  1...e6 (5):  2.d4 5/5 c5 (3) 3.d5 3/3 Qa5+ 4.Nc3
  1...c5 (4):  2.d4 4/4 cxd4 3.Nf3
  1...f5 (3):  2.exf5 3/3 Nf6 3.d4 d5 4.Bd3 Nc6 5.Nf3 e6 6.O-O
```

Most common 10-ply: 9x `e4 Nf6 d4 d6 Nc3 e5 dxe5 dxe5 Qxd8+ Kxd8` (we trade queens by ply 9
whenever allowed), 3x `e4 d5 exd5 Qxd5 Nc3 Qd8 Be2 c5 Nf3 Nc6`, 3x `... Nc3 Qe6 Be2 Bd7 Nf3
Qg6`.

### As black (75 games): 1...d5 65, 1...Nf6 10

| n | our moves 1-6 |
|---|---|
| 7 | d5 e6 exd5 c6 Nf6 Be7 |
| 4 | d5 e6 exd5 c6 Be7 Nf6 |
| 4 | d5 Nf6 c6 Nbd7 e5 Nh5 |
| 3 | d5 dxe4 c6 Nf6 Bf5 e6 |
| 3 | d5 Nf6 c5 cxd4 Nc6 a6 |

56 distinct in 75 games. Against 1.d4 d5 2.c4 (22) we answer 2...e6 19/22 and reach the same
Exchange QGD structure GG plays as white (`d4 d5 c4 e6 cxd5 exd5 Bf4 c6 e3 Nf6` 7 times).
Against 2.Bf4 (13) 2...Nf6 13/13, then ...c5 6 or ...c6 5.

Both bots castle early (GG 166/179 games, median ply 17; ours 126/150, median ply 18) and
both keep the king on g1/g8 at ply 40 (GG 122/171, ours 95/136). Piece-type shares in the
first 20 plies are nearly identical (GG: P .46 N .24 B .19 castle .06 Q .03 R .02; ours:
P .45 N .29 B .13 castle .05 Q .05 R .04); we develop bishops less and move the queen and
rooks slightly more.

The opening is not where the gap is. Material balance (subject minus opponent, mean over
games still running, pawn=1 N=B=3 R=5 Q=9):

| ply | GG | ahead/behind | ours | ahead/behind |
|---|---|---|---|---|
| 10 | +0.01 | 17/17 | +0.35 | 40/19 |
| 20 | +0.14 | 39/25 | +0.02 | 35/61 |
| 30 | +0.84 | 60/31 | -0.28 | 45/59 |
| 40 | +1.55 | 84/32 | -0.34 | 52/67 |
| 50 | +1.84 | 90/29 | -0.53 | 52/55 |
| 60 | +2.73 | 96/23 | -0.65 | 46/49 |
| 80 | +2.64 | 79/16 | -0.13 | 27/26 |

We are slightly ahead at ply 10 and behind from ply 20 on; GG is level at ply 10 and pulls
away steadily. Supporting numbers:

- Material left en prise after an own move (full information; opponent's best capture
  gain = victim value minus captor value if the square is defended): GG leaves >= 3 points
  hanging on 5.9% of its moves, its opponents 7.9%; we do so on 9.0% of ours, our opponents
  8.2%. Mean hanging value per move: GG 0.39, ours 0.62.
- Captures in the first 40 plies: opponents make 2.15 unanswered captures per game against
  GG, 3.47 against us.
- Queen: ours is captured by ply 40 in 61/150 games (41%), GG's in 38/179 (21%). Median ply
  of queen loss: ours 36, GG 52. In 87/111 of our queen losses the queen had just moved to the
  square where it was taken, and in 100/111 the captor was on a square we could see. 73 of
  those losses got no compensation on the next ply (GG: 62/125, but with 50 queen-for-queen).
- King exposure at ply 40 (enemy-attacked squares in the king's 3x3 zone / enemy pieces
  within distance 2): GG 0.57 / 0.11, GG's opponents 0.79 / 0.17, ours 0.68 / 0.07, our
  opponents 1.21 / 0.29. At ply 20 GG's king zone is attacked 0.22 squares on average with no
  enemy piece ever within 2 squares; ours 0.51 / 0.09.

## 4. Vision: no difference in the opening

Visible squares (count of non-`?` squares in the side's view) after each ply, averaged over
games. Columns: GG and its opponent over all games, ours and our opponent over all games;
then split by colour.

| ply | GG | GG opp | ours | our opp | GG as W | opp B | ours as W | opp B | GG as B | opp W | ours as B | opp W |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 | 32.0 |
| 1 | 33.5 | 33.3 | 33.5 | 33.3 | 35.0 | 32.0 | 35.0 | 32.0 | 32.0 | 34.7 | 32.0 | 34.5 |
| 2 | 33.6 | 34.1 | 34.8 | 34.2 | 34.7 | 33.6 | 35.5 | 34.3 | 32.5 | 34.7 | 34.2 | 34.0 |
| 3 | 34.2 | 34.8 | 35.7 | 34.5 | 35.9 | 33.6 | 37.1 | 33.4 | 32.5 | 36.0 | 34.4 | 35.5 |
| 4 | 35.2 | 35.5 | 36.0 | 36.4 | 36.0 | 34.9 | 36.5 | 37.4 | 34.3 | 36.0 | 35.6 | 35.4 |
| 5 | 35.9 | 36.0 | 36.4 | 36.9 | 37.9 | 34.5 | 37.5 | 37.1 | 33.9 | 37.5 | 35.3 | 36.6 |
| 6 | 35.8 | 36.1 | 36.6 | 36.8 | 37.2 | 35.2 | 37.1 | 37.3 | 34.4 | 37.1 | 36.2 | 36.4 |
| 7 | 36.6 | 36.8 | 36.9 | 37.3 | 38.8 | 35.1 | 37.6 | 36.9 | 34.3 | 38.6 | 36.2 | 37.7 |
| 8 | 36.8 | 37.1 | 36.8 | 37.7 | 38.6 | 36.1 | 37.2 | 38.2 | 35.1 | 38.1 | 36.4 | 37.2 |
| 9 | 37.6 | 37.3 | 37.2 | 38.3 | 40.2 | 35.6 | 38.3 | 37.3 | 34.9 | 39.1 | 36.0 | 39.3 |
| 10 | 38.0 | 37.5 | 37.1 | 38.2 | 39.7 | 36.3 | 36.8 | 38.2 | 36.3 | 38.8 | 37.5 | 38.2 |
| 11 | 38.3 | 37.7 | 37.5 | 38.5 | 40.6 | 35.9 | 38.5 | 37.2 | 36.0 | 39.6 | 36.5 | 39.8 |
| 12 | 38.5 | 37.9 | 37.9 | 38.1 | 40.0 | 36.5 | 38.2 | 37.5 | 36.9 | 39.2 | 37.7 | 38.8 |
| 13 | 38.5 | 38.0 | 38.0 | 38.4 | 40.9 | 36.1 | 39.3 | 36.8 | 36.1 | 39.9 | 36.8 | 40.0 |
| 14 | 38.5 | 38.3 | 38.5 | 38.4 | 40.3 | 37.0 | 38.8 | 37.9 | 36.7 | 39.5 | 38.2 | 39.0 |
| 15 | 38.4 | 38.3 | 38.5 | 38.3 | 40.9 | 36.3 | 39.9 | 36.8 | 35.9 | 40.4 | 37.1 | 39.7 |
| 16 | 38.5 | 38.5 | 38.5 | 38.4 | 40.2 | 37.4 | 39.0 | 37.4 | 36.7 | 39.6 | 38.0 | 39.3 |
| 17 | 38.3 | 38.3 | 38.7 | 38.1 | 40.6 | 36.4 | 40.0 | 36.3 | 36.0 | 40.3 | 37.4 | 39.8 |
| 18 | 38.4 | 38.6 | 38.8 | 38.3 | 40.0 | 37.6 | 39.0 | 37.5 | 36.9 | 39.6 | 38.6 | 39.1 |
| 19 | 38.3 | 38.3 | 39.1 | 38.2 | 40.7 | 36.4 | 40.4 | 36.6 | 35.9 | 40.3 | 37.9 | 39.8 |
| 20 | 38.7 | 38.4 | 39.2 | 38.4 | 40.2 | 37.6 | 39.6 | 37.7 | 37.1 | 39.3 | 38.9 | 39.1 |

Mean over plies 1-20: GG 37.1, GG's opponents 37.1, ours 37.3, our opponents 37.3. GG sees
no more of the board than anyone else; its opening does not optimise vision. (The
white-side numbers are higher for both bots because white has moved once more at odd plies.)

## 5. Time management

Seconds spent per own move (increment added back) by ply:

| | plies 1-10 | 11-30 | 31-60 | 61-100 | 101+ | clock at game end |
|---|---|---|---|---|---|---|
| GG | 6.1 | 6.8 | 5.9 | 3.8 | 2.1 | mean 37 s, min 12 s |
| GG's opponents | 5.0 | 5.5 | 4.4 | 3.3 | 2.3 | |
| Ours | 5.0 | 5.5 | 4.6 | 3.6 | 2.5 | mean 84 s, min 19 s |
| our opponents | 4.0 | 5.2 | 4.1 | 3.1 | 2.2 | |

GG's spend is a function of remaining clock: 7.2 s/move with 120-140 s left, 5.2 s with
40-60 s, 2.3 s under 20 s (1623 of its 8110 moves are played with under 20 s left; we
played 9 such moves). It runs the clock down to about 12 s and never forfeits. We finish
games with 84 s unused on average, i.e. GG gets roughly 1.3-1.5x our thinking time per move
through the middlegame and more than that in long games.

## 6. Greek Gift's 11 losses and 5 draws

Losses (all King capturable, none under 38 plies, all with the attacker unseen): 7 were
unseen checks it failed to escape (3 of them with no safe move available), 4 were walking
into an unseen attacker late in lost positions (material down 9-20 points in 9 of 11). The
5 draws are threefold repetitions with roughly level material and 12-35 s on its clock.

## 7. Summary of what Greek Gift does differently

1. Not the opening. 1.d4 with c4/cxd5 or Bf4, e3, Nc3, Bd3, short castle; as black ...c6 ...d5
   or ...Nf6 ...g6 ...Bg7 O-O. Mainstream, quiet, randomized between 2-3 book-like choices.
   No early queen sorties, no raids; nothing ends before ply 34. Vision in the first 20
   plies is identical to everyone else's.
2. Not catastrophes in the opening: 0 games lost before ply 38; we lost 2 before ply 20.
3. It stops hanging material: 5.9% of its moves leave >= 3 points en prise vs our 9.0%; its
   queen survives to ply 40 in 79% of games vs our 59%; opponents get 2.15 free captures in
   the first 40 plies vs 3.47 against us. It is +0.84 at ply 30 and +2.73 at ply 60 on
   average; we are -0.28 and -0.65.
4. Its king does not step into unseen attacks: 3 such losses in 179 games vs 35 in our 150
   (55% of all our losses). Its king zone is attacked less (0.57 vs 0.68 squares at ply 40)
   and it gets checked 40% less often per move than we do.
5. It converts with heavy pieces late (Q and R are the killers in 130 of 163 wins, mean ply
   90) and it uses its clock: 1.3-1.5x our time per move, finishing with 37 s vs our 84 s.
