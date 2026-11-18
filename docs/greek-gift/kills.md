# Greek Gift v30 on the arena: how it wins, how it loses

Scope: all 179 arena games of Greek Gift (id f394d843…, v30 throughout): 163 wins, 11 losses, 5 draws. Comparison set: the 150 arena games of Magnus Monte Carlsen v4 (82-4-64). Everything below is replayed with `starter/referee.py` `FowBoard` from the replay frames; views are the frames' own `white`/`black` strings. Scripts: `gg/kw/replay_rows.py` (per-game rows), `gg/kw/report.py`, `gg/kw/extras.py`; raw outputs `gg/kw/report_raw.md`, `gg/kw/extras_raw.md` (both reproduced in full below).

## Summary

**How it wins: material first, then a king hunt with pieces the loser cannot see.**

- At the kill Greek Gift is ahead by a mean of **+8.4** (median +8). 133/163 wins (82%) are at >= +3, 111/163 (68%) at >= +6, and only 11/163 (7%) at <= 0. Ten plies earlier the mean edge is already +4.7. It is not catching kings while material is even.
- The edge is built in the middlegame: mean balance +0.1 at ply 20, +1.0 at ply 30, +1.8 at ply 40, +3.4 at ply 60 (wins). Its first material lead comes at median ply 18, and in 104/177 games it is a single pawn; the capture that produced the first lead had an unseen capturer only 17% of the time. The decisive gains come later: 41% of all its captures are by a piece the victim could not see (vs 35% for its opponents), worth 10.4 points per game vs 7.8 lost the same way, net **+2.6 per game** (+3.3 in wins). The net from seen captures is only +2.1; promotions add +1.5. So roughly half of its material edge is from unseen captures. It also promotes 0.22 times a game vs 0.04 for its opponents.
- The kill itself: 104/163 `check_unanswered` (its move attacked the king and the loser did not answer) and 59/163 `walked_in`. Attacker Q 66, R 62, N 13, B 10, K 10, P 2 (R+Q 79%), mean distance 3.0 king steps; in 117/163 the attacking piece arrived with the killer's last move (`line` = 0), and the loser saw the attacker before the fatal ply in only **8/163** (0/59 of the walked-in kills). In 60 of the 104 check cases the loser still had a safe move; in 44 it was mated.
- A real "Greek gift" pattern is in there: in 40/163 wins its last move put the moved piece on a square the loser attacked (bait: Q 23, R 10, P 4, N 2, B 1) and in 27 of those the loser captured the bait with its fatal move: the loser's king took the queen in 14 games and a hidden rook/knight/bishop then took the king. 17/163 wins end with the loser capturing Greek Gift's queen.
- Against us (6 games) the picture is the same: +7.8 at the kill, 4 walked-in, our king moved on every fatal ply, 0/6 saw the attacker. Our v4's own wins have the same anatomy as its (+8.5 at the kill, 33/81 bait); the difference is upstream: we reach a material edge less often and give material to unseen attackers as often as we take it (9.2 vs 9.3 per game, net −0.1; GG net +2.6).

**How it loses: it falls behind in material, and it runs out of clock.**

- 11 losses: 7 as black, 4 as white; to Crimson Fog (2, v4), duck (2, v11), Farsight, Strongly Invisible, Decent Chess Bot, HYPOTHERMIA, Gravel Road, Foggy Fischer, Cranberry Lemon. All the opponents that beat it are rated 1850-2030; nobody below 1849 beat it.
- In 9/11 losses it was down 8 to 20 points before the fatal ply; the other two were level (HYPOTHERMIA, 48 plies, +0; Foggy Fischer, 134 plies, +1, a K+N vs K ending where its king walked into a knight). Its opponents in the losses took 14.2 points per game with unseen attackers vs 7.9 for GG. The kills: 7 check_unanswered, 4 walked_in; attacker Q 5, R 4, N 2; it never saw the attacker (0/11); 7 fatal moves were king moves. In 4 of the 7 check cases it had a safe move and did not find it.
- **Clock.** 180+2. Greek Gift spends 6.3-6.8 s per move for the first 40 plies and reaches a mean of 24 s left at ply 80 and 15 s at ply 100, after which it plays at 2 s per move (the increment). Its opponents keep 70 s at ply 80. Its clock went under 20 s in 90/179 games (79 wins, 4 draws, 7 losses): every draw and 7/11 losses happened with it under 20 s, and in 8 of the 11 losses it finished with 12-15 s. All 5 draws are threefold repetitions at 12-17 s on its clock (one at 35 s, +6 material, vs RATIRL). It still gains material after going under 20 s (+3.3 on average), so time trouble blunts rather than breaks it, but it is where the non-wins come from. Our v4 keeps 71 s at ply 80.

**What to take from it (for our bot).** The kill mechanics are not what separates it from v4: both kill at +8 with an unseen R/Q, both bait with the queen. The gap is (a) getting ahead by ply 40-60 (49% of its games ahead at ply 40, 69% at 60, vs 38%/45% for v4), driven by capturing with pieces the victim cannot see (41% of captures) while giving back less (35%), and (b) converting: it reaches >= +3 in 157/163 wins and then takes a median 55 plies to find the king. Its weak spot is the clock after ply 80, and long games as black.

# Greek Gift v30: how it wins and how it loses

Data: 179 arena games of Greek Gift (id f394d843..., v30 in every game: 179), 163 wins, 11 losses, 5 draws; our comparison set: 150 games of Magnus Monte Carlsen v4 (Counter({'win': 82, 'loss': 64, 'draw': 4})). Replayed with starter/referee.py FowBoard; views taken from the replay frames.
Greek Gift was white in 90 games, black in 89.
Record by colour: white Counter({'win': 85, 'loss': 4, 'draw': 1}), black Counter({'win': 78, 'loss': 7, 'draw': 4}).

Definitions (same as docs/arena-opponents.md section 3): the fatal ply is the loser's last move. `check_unanswered` = the winner's previous move already attacked the loser's king and the loser's move did not remove the attack; `walked_in` = the king was not attacked before the loser's move and is after it. Attacker = the piece the winner moved on its last move if it attacks the king (check cases), otherwise the lowest-valued attacker of the king square. Distance = king steps between attacker and king. `line` = number of consecutive plies before the winner's last move during which that attacker already stood on its square attacking the death square (0 = the winner's last move put it there, or the loser moved into a line that had been set up by the winner's last move). `loser saw attacker` = the loser's view before its fatal move showed the attacker's square. Material = P1 N3 B3 R5 Q9, winner minus loser, before the fatal move (`at kill`) and 10 plies earlier.

## 1. The 163 wins

Game length (plies): mean 90, median 85, min 34, max 326.
| plies | <=40 | 41-60 | 61-80 | 81-100 | 101-140 | >140 |
|---|---|---|---|---|---|---|
| wins | 9 | 32 | 32 | 39 | 35 | 16 |
As white: mean 84 plies (n=85); as black: mean 96 (n=78).

**All 163 wins** (163 games)

| | value |
|---|---|
| kind | check_unanswered: 104, walked_in: 59 |
| attacker piece | Q: 66, R: 62, N: 13, B: 10, K: 10, P: 2 |
| R+Q share | 79% |
| attacker distance (king steps) | 1: 30, 2: 47, 3: 33, 4: 19, 5: 17, 6: 12, 7: 5 (mean 3.0) |
| plies attacker already on the striking line | 0: 117, 2: 25, 3: 1, 4: 7, 5: 1, 6: 4, 8: 2, 12: 2, 18: 1, 25: 1, 30: 1, 58: 1 |
| loser saw the attacker before the fatal ply | 8/163 |
| king-neighbour squares the winner saw (of 8) | 0: 2, 1: 36, 2: 33, 3: 29, 4: 29, 5: 15, 6: 7, 7: 4, 8: 8 (mean 3.2) |
| attacking move was a capture (check cases) | 26/104 |
| discovered attack (check cases) | 31/104 |
| number of winner pieces attacking the king at the end | 1: 161, 2: 1, 3: 1 |
| loser's fatal move | king_move: 76, other: 45, king_capture: 24, capture: 18 |
| loser's fatal move captured (piece) | Q: 17, P: 11, R: 10, N: 3, B: 1 |
| winner's last move put the moved piece en prise (bait, piece) | 40/163: Q: 23, R: 10, P: 4, N: 2, B: 1 |
| bait taken by the fatal move (loser captured the bait and died) | 27/163 |
| loser's king square at death | h8: 11, g1: 9, g7: 9, g8: 8, h7: 7, g4: 6, h1: 6, a7: 5 |
| material winner-loser at kill | mean +8.4, median +8 |
| material winner-loser 10 plies before | mean +4.7, median +5 |
| material at kill, buckets | <=-3: 2, -2..-1: 3, 0: 6, +1..+2: 19, +3..+5: 22, +6..+9: 43, >=+10: 68 |
| material 10 plies before, buckets | <=-3: 0, -2..-1: 7, 0: 21, +1..+2: 28, +3..+5: 43, +6..+9: 47, >=+10: 17 |
| wins with material <= 0 at kill | 11/163 (7%) |
| wins with material >= +3 at kill | 133/163 (82%) |

**Wins where the loser walked in** (59 games)

| | value |
|---|---|
| kind | walked_in: 59 |
| attacker piece | Q: 20, R: 20, K: 8, N: 5, B: 4, P: 2 |
| R+Q share | 68% |
| attacker distance (king steps) | 1: 16, 2: 14, 3: 12, 4: 8, 5: 5, 6: 2, 7: 2 (mean 2.8) |
| plies attacker already on the striking line | 0: 30, 2: 16, 3: 1, 4: 4, 6: 3, 8: 2, 12: 1, 30: 1, 58: 1 |
| loser saw the attacker before the fatal ply | 0/59 |
| king-neighbour squares the winner saw (of 8) | 0: 1, 1: 11, 2: 13, 3: 13, 4: 11, 5: 6, 6: 3, 7: 1 (mean 3.0) |
| attacking move was a capture (check cases) | 0/0 |
| discovered attack (check cases) | 0/0 |
| number of winner pieces attacking the king at the end | 1: 59 |
| loser's fatal move | king_move: 52, king_capture: 4, other: 2, capture: 1 |
| loser's fatal move captured (piece) | R: 3, N: 1, P: 1 |
| winner's last move put the moved piece en prise (bait, piece) | 6/59: R: 3, P: 2, N: 1 |
| bait taken by the fatal move (loser captured the bait and died) | 4/59 |
| loser's king square at death | e7: 4, g4: 4, g3: 3, g6: 3, g7: 3, h7: 3, d7: 2, e3: 2 |
| material winner-loser at kill | mean +7.2, median +7 |
| material winner-loser 10 plies before | mean +4.4, median +5 |
| material at kill, buckets | <=-3: 1, -2..-1: 2, 0: 2, +1..+2: 7, +3..+5: 8, +6..+9: 20, >=+10: 19 |
| material 10 plies before, buckets | <=-3: 0, -2..-1: 3, 0: 6, +1..+2: 11, +3..+5: 16, +6..+9: 19, >=+10: 4 |
| wins with material <= 0 at kill | 5/59 (8%) |
| wins with material >= +3 at kill | 47/59 (80%) |

**Wins where the loser did not answer the attack** (104 games)

| | value |
|---|---|
| kind | check_unanswered: 104 |
| attacker piece | Q: 46, R: 42, N: 8, B: 6, K: 2 |
| R+Q share | 85% |
| attacker distance (king steps) | 1: 14, 2: 33, 3: 21, 4: 11, 5: 12, 6: 10, 7: 3 (mean 3.2) |
| plies attacker already on the striking line | 0: 87, 2: 9, 4: 3, 5: 1, 6: 1, 12: 1, 18: 1, 25: 1 |
| loser saw the attacker before the fatal ply | 8/104 |
| king-neighbour squares the winner saw (of 8) | 0: 1, 1: 25, 2: 20, 3: 16, 4: 18, 5: 9, 6: 4, 7: 3, 8: 8 (mean 3.3) |
| attacking move was a capture (check cases) | 26/104 |
| discovered attack (check cases) | 31/104 |
| number of winner pieces attacking the king at the end | 1: 102, 2: 1, 3: 1 |
| loser's fatal move | other: 43, king_move: 24, king_capture: 20, capture: 17 |
| loser's fatal move captured (piece) | Q: 17, P: 10, R: 7, N: 2, B: 1 |
| winner's last move put the moved piece en prise (bait, piece) | 34/104: Q: 23, R: 7, P: 2, B: 1, N: 1 |
| bait taken by the fatal move (loser captured the bait and died) | 23/104 |
| loser's king square at death | h8: 11, g1: 8, g8: 7, g7: 6, a7: 4, g2: 4, h1: 4, h7: 4 |
| material winner-loser at kill | mean +9.0, median +9 |
| material winner-loser 10 plies before | mean +4.9, median +5 |
| material at kill, buckets | <=-3: 1, -2..-1: 1, 0: 4, +1..+2: 12, +3..+5: 14, +6..+9: 23, >=+10: 49 |
| material 10 plies before, buckets | <=-3: 0, -2..-1: 4, 0: 15, +1..+2: 17, +3..+5: 27, +6..+9: 28, >=+10: 13 |
| wins with material <= 0 at kill | 6/104 (6%) |
| wins with material >= +3 at kill | 86/104 (83%) |

**Wins against us (Magnus Monte Carlsen)** (6 games)

| | value |
|---|---|
| kind | walked_in: 4, check_unanswered: 2 |
| attacker piece | Q: 3, B: 1, P: 1, R: 1 |
| R+Q share | 67% |
| attacker distance (king steps) | 1: 3, 2: 1, 4: 2 (mean 2.2) |
| plies attacker already on the striking line | 0: 3, 2: 1, 6: 1, 12: 1 |
| loser saw the attacker before the fatal ply | 0/6 |
| king-neighbour squares the winner saw (of 8) | 2: 1, 3: 2, 4: 3 (mean 3.3) |
| attacking move was a capture (check cases) | 2/2 |
| discovered attack (check cases) | 1/2 |
| number of winner pieces attacking the king at the end | 1: 6 |
| loser's fatal move | king_move: 5, king_capture: 1 |
| loser's fatal move captured (piece) | R: 1 |
| winner's last move put the moved piece en prise (bait, piece) | 1/6: R: 1 |
| bait taken by the fatal move (loser captured the bait and died) | 1/6 |
| loser's king square at death | e7: 2, e8: 1, f1: 1, g3: 1, g5: 1 |
| material winner-loser at kill | mean +7.8, median +8 |
| material winner-loser 10 plies before | mean +4.3, median +5 |
| material at kill, buckets | <=-3: 1, -2..-1: 0, 0: 0, +1..+2: 0, +3..+5: 1, +6..+9: 2, >=+10: 2 |
| material 10 plies before, buckets | <=-3: 0, -2..-1: 1, 0: 1, +1..+2: 0, +3..+5: 2, +6..+9: 1, >=+10: 1 |
| wins with material <= 0 at kill | 1/6 (17%) |
| wins with material >= +3 at kill | 5/6 (83%) |

**Reference: MMC v4's own wins with a king capture (same metrics)** (81 games)

| | value |
|---|---|
| kind | check_unanswered: 58, walked_in: 23 |
| attacker piece | Q: 37, R: 28, B: 10, N: 5, K: 1 |
| R+Q share | 80% |
| attacker distance (king steps) | 1: 20, 2: 19, 3: 18, 4: 13, 5: 5, 6: 4, 7: 2 (mean 2.8) |
| plies attacker already on the striking line | 0: 62, 1: 1, 2: 9, 4: 4, 6: 2, 8: 1, 16: 1, 36: 1 |
| loser saw the attacker before the fatal ply | 11/81 |
| king-neighbour squares the winner saw (of 8) | 0: 1, 1: 12, 2: 20, 3: 14, 4: 12, 5: 13, 6: 3, 7: 1, 8: 5 (mean 3.4) |
| attacking move was a capture (check cases) | 20/58 |
| discovered attack (check cases) | 23/58 |
| number of winner pieces attacking the king at the end | 1: 77, 2: 4 |
| loser's fatal move | king_move: 37, other: 19, king_capture: 15, capture: 10 |
| loser's fatal move captured (piece) | P: 7, Q: 7, R: 7, B: 3, N: 1 |
| winner's last move put the moved piece en prise (bait, piece) | 33/81: Q: 19, R: 10, P: 3, B: 1 |
| bait taken by the fatal move (loser captured the bait and died) | 16/81 |
| loser's king square at death | g1: 6, g7: 6, h1: 6, e8: 4, g8: 4, c8: 3, e1: 3, h7: 3 |
| material winner-loser at kill | mean +8.5, median +9 |
| material winner-loser 10 plies before | mean +5.0, median +6 |
| material at kill, buckets | <=-3: 4, -2..-1: 2, 0: 3, +1..+2: 6, +3..+5: 11, +6..+9: 18, >=+10: 37 |
| material 10 plies before, buckets | <=-3: 3, -2..-1: 4, 0: 6, +1..+2: 9, +3..+5: 18, +6..+9: 29, >=+10: 12 |
| wins with material <= 0 at kill | 9/81 (11%) |
| wins with material >= +3 at kill | 66/81 (81%) |

**Reference: MMC v4's 64 losses (winner = opponent)** (64 games)

| | value |
|---|---|
| kind | walked_in: 38, check_unanswered: 26 |
| attacker piece | Q: 28, R: 19, B: 6, K: 5, N: 4, P: 2 |
| R+Q share | 73% |
| attacker distance (king steps) | 1: 13, 2: 14, 3: 12, 4: 13, 5: 6, 6: 4, 7: 2 (mean 3.1) |
| plies attacker already on the striking line | 0: 39, 1: 1, 2: 7, 4: 4, 5: 1, 6: 5, 7: 1, 10: 1, 12: 2, 14: 1, 22: 1, 42: 1 |
| loser saw the attacker before the fatal ply | 1/64 |
| king-neighbour squares the winner saw (of 8) | 0: 1, 1: 11, 2: 12, 3: 15, 4: 13, 5: 6, 6: 4, 7: 1, 8: 1 (mean 3.1) |
| attacking move was a capture (check cases) | 12/26 |
| discovered attack (check cases) | 11/26 |
| number of winner pieces attacking the king at the end | 1: 64 |
| loser's fatal move | king_move: 35, other: 13, king_capture: 12, capture: 4 |
| loser's fatal move captured (piece) | R: 7, N: 4, P: 3, B: 1, Q: 1 |
| winner's last move put the moved piece en prise (bait, piece) | 12/64: R: 6, N: 3, Q: 2, P: 1 |
| bait taken by the fatal move (loser captured the bait and died) | 9/64 |
| loser's king square at death | e7: 5, h2: 4, d2: 3, f5: 3, f7: 3, f8: 3, g1: 3, h7: 3 |
| material winner-loser at kill | mean +8.7, median +8 |
| material winner-loser 10 plies before | mean +6.8, median +6 |
| material at kill, buckets | <=-3: 1, -2..-1: 2, 0: 2, +1..+2: 10, +3..+5: 7, +6..+9: 14, >=+10: 28 |
| material 10 plies before, buckets | <=-3: 1, -2..-1: 4, 0: 5, +1..+2: 8, +3..+5: 12, +6..+9: 12, >=+10: 22 |
| wins with material <= 0 at kill | 5/64 (8%) |
| wins with material >= +3 at kill | 49/64 (77%) |

Kill kind against material edge at the kill:

| material at kill | walked_in | check_unanswered | total | mean plies |
|---|---|---|---|---|
| <= -1 | 3 | 2 | 5 | 88 |
| 0 | 2 | 4 | 6 | 64 |
| +1..+2 | 7 | 12 | 19 | 76 |
| +3..+5 | 8 | 14 | 22 | 89 |
| +6..+9 | 20 | 23 | 43 | 97 |
| >= +10 | 19 | 49 | 68 | 92 |

Shortest 12 wins:

| opp | colour | plies | kind | attacker | from | king | fatal move | material at kill |
|---|---|---|---|---|---|---|---|---|
| Mist Opportunities | W | 34 | check_unanswered | R | g1 | g7 | king_capture g8g7 | +1 |
| TA Baseline S | W | 36 | check_unanswered | Q | g5 | d8 | other c8b7 | +4 |
| Cross-Registered Playe | W | 36 | walked_in | R | d1 | d7 | king_move e8d7 | +2 |
| In Pawn Sight | B | 37 | check_unanswered | Q | e6 | e1 | other h1h2 | -2 |
| Knight Vision | W | 38 | walked_in | B | h3 | d7 | capture e6d5 | +2 |
| TA Baseline A | W | 38 | check_unanswered | R | h1 | h7 | king_capture h8h7 | +0 |
| IAmAVirus | W | 38 | check_unanswered | Q | h7 | g8 | other c4c3 | +0 |
| Resting Bishop Faces | W | 40 | check_unanswered | R | d1 | d8 | capture d7b6 | +7 |
| Fogbreakers | W | 40 | check_unanswered | R | e8 | b8 | other a6c7 | +8 |
| Fogitos | W | 42 | check_unanswered | N | f6 | g8 | other b5b4 | +10 |
| ADARSH | W | 42 | check_unanswered | Q | f8 | h8 | other b8c8 | +23 |
| Gravel Road | W | 44 | check_unanswered | R | h7 | h8 | other e5e4 | +0 |

Per opponent (wins):

| opponent | n | plies mean | check / walked_in | pieces | mean dist | line>0 | loser saw | material at kill mean | fatal move |
|---|---|---|---|---|---|---|---|---|---|
| Cranberry Lemon | 11 | 109 | 8 / 3 | R:6 Q:3 K:2 | 3.0 | 3 | 1 | +10.6 | king_move:7 king_capture:2 capture:1 other:1 |
| Strongly Invisible | 11 | 111 | 4 / 7 | Q:8 R:2 B:1 | 2.6 | 5 | 1 | +8.6 | king_move:7 other:3 capture:1 |
| Farsight | 10 | 81 | 4 / 6 | R:4 Q:3 N:2 K:1 | 2.3 | 4 | 1 | +8.7 | king_move:9 other:1 |
| IAmAVirus | 10 | 80 | 7 / 3 | Q:5 R:2 B:2 K:1 | 3.3 | 0 | 1 | +8.9 | other:5 king_move:4 king_capture:1 |
| Decent Chess Bot | 9 | 108 | 5 / 4 | R:4 Q:3 N:1 P:1 | 2.0 | 1 | 0 | +9.6 | other:4 king_move:4 king_capture:1 |
| TA Baseline S | 8 | 82 | 6 / 2 | Q:3 R:3 B:2 | 3.5 | 3 | 1 | +10.0 | king_move:4 capture:3 other:1 |
| Crimson Fog | 8 | 80 | 8 / 0 | Q:4 R:3 N:1 | 2.6 | 0 | 0 | +7.6 | other:4 king_move:2 capture:1 king_capture:1 |
| Team 319 | 8 | 87 | 3 / 5 | R:3 K:2 Q:2 N:1 | 2.8 | 4 | 0 | +4.8 | king_move:6 other:1 king_capture:1 |
| Gravel Road | 7 | 107 | 2 / 5 | R:3 Q:2 N:1 K:1 | 2.7 | 4 | 1 | +6.6 | king_move:6 other:1 |
| Knight Vision | 6 | 62 | 4 / 2 | Q:2 N:2 R:1 B:1 | 3.2 | 3 | 0 | +3.5 | king_capture:3 king_move:2 capture:1 |
| Lost Signal | 6 | 98 | 2 / 4 | R:4 N:1 Q:1 | 4.3 | 2 | 0 | +6.0 | king_move:4 other:1 king_capture:1 |
| Resting Bishop Faces | 6 | 96 | 3 / 3 | R:3 Q:2 N:1 | 3.8 | 3 | 0 | +4.3 | king_move:3 king_capture:2 capture:1 |
| Instructors | 6 | 84 | 5 / 1 | Q:3 B:2 R:1 | 1.8 | 2 | 0 | +10.7 | king_move:3 other:3 |
| HYPOTHERMIA | 6 | 105 | 6 / 0 | R:3 Q:2 N:1 | 2.8 | 1 | 0 | +11.5 | capture:3 other:2 king_capture:1 |
| duck | 6 | 108 | 3 / 3 | Q:4 K:1 R:1 | 3.0 | 0 | 0 | +8.5 | king_move:3 capture:2 king_capture:1 |
| Magnus Monte Carlsen | 6 | 92 | 2 / 4 | Q:3 P:1 B:1 R:1 | 2.2 | 3 | 0 | +7.8 | king_move:5 king_capture:1 |
| Foggy Fischer | 5 | 84 | 5 / 0 | Q:3 R:2 | 3.2 | 2 | 0 | +11.6 | other:2 king_capture:2 capture:1 |
| Cross-Registered Players | 4 | 107 | 1 / 3 | K:1 N:1 Q:1 R:1 | 2.8 | 2 | 0 | +6.8 | king_move:3 other:1 |
| Mist Opportunities | 4 | 70 | 4 / 0 | R:4 | 5.0 | 0 | 0 | +5.2 | king_capture:2 capture:1 other:1 |
| Next | 3 | 115 | 1 / 2 | Q:2 K:1 | 1.7 | 3 | 0 | +9.3 | king_move:2 king_capture:1 |
| RATIRL | 3 | 50 | 3 / 0 | R:2 Q:1 | 3.3 | 0 | 0 | +7.3 | capture:1 other:1 king_capture:1 |
| In Pawn Sight | 2 | 60 | 2 / 0 | Q:2 | 5.5 | 0 | 0 | +5.0 | other:2 |
| TA Baseline A | 2 | 44 | 2 / 0 | B:1 R:1 | 4.5 | 1 | 0 | +7.0 | king_capture:2 |
| Sausage | 2 | 54 | 2 / 0 | R:2 | 5.0 | 0 | 0 | +15.0 | other:1 capture:1 |
| Unicorns | 2 | 64 | 1 / 1 | Q:2 | 3.0 | 0 | 1 | +2.0 | king_move:1 king_capture:1 |
| TA Baseline P | 2 | 62 | 2 / 0 | R:1 Q:1 | 3.5 | 0 | 0 | +16.0 | other:2 |
| Fogitos | 2 | 84 | 2 / 0 | Q:1 N:1 | 2.5 | 0 | 1 | +10.5 | other:2 |
| Fogbreakers | 2 | 102 | 2 / 0 | Q:1 R:1 | 2.5 | 0 | 0 | +6.0 | other:2 |
| Ex Republics | 2 | 74 | 1 / 1 | R:2 | 4.5 | 0 | 0 | +7.5 | other:1 king_move:1 |
| ADARSH | 2 | 80 | 2 / 0 | R:1 Q:1 | 3.5 | 0 | 0 | +19.0 | capture:1 other:1 |
| TUM | 2 | 94 | 2 / 0 | Q:1 R:1 | 3.5 | 0 | 0 | +9.5 | other:2 |

## 2. Material trajectory and how the first material is won

Mean material balance (the named bot minus its opponent) in the position after N plies, over games that lasted at least N plies; `>0` = share of games where it is ahead.

| games | ply 10 | ply 20 | ply 30 | ply 40 | ply 60 | ply 80 |
|---|---|---|---|---|---|---|
| Greek Gift, all 179 | +0.01 (n=179, >0: 9%, <0: 9%) | +0.14 (n=179, >0: 22%, <0: 14%) | +0.84 (n=179, >0: 34%, <0: 17%) | +1.55 (n=171, >0: 49%, <0: 19%) | +2.73 (n=139, >0: 69%, <0: 17%) | +2.64 (n=104, >0: 76%, <0: 15%) |
| Greek Gift, 163 wins | +0.01 (n=163, >0: 9%, <0: 10%) | +0.10 (n=163, >0: 21%, <0: 14%) | +1.03 (n=163, >0: 36%, <0: 15%) | +1.83 (n=156, >0: 52%, <0: 16%) | +3.35 (n=125, >0: 74%, <0: 12%) | +3.57 (n=92, >0: 84%, <0: 10%) |
| Greek Gift, 11 losses | +0.09 (n=11, >0: 9%, <0: 0%) | +0.45 (n=11, >0: 27%, <0: 9%) | -1.00 (n=11, >0: 18%, <0: 36%) | -2.00 (n=10, >0: 20%, <0: 50%) | -4.78 (n=9, >0: 22%, <0: 67%) | -6.25 (n=8, >0: 25%, <0: 62%) |
| Greek Gift vs us (n=6) | -0.17 (n=6, >0: 0%, <0: 17%) | +0.67 (n=6, >0: 67%, <0: 0%) | +2.33 (n=6, >0: 50%, <0: 17%) | +0.83 (n=6, >0: 50%, <0: 33%) | +3.25 (n=4, >0: 75%, <0: 25%) | +1.67 (n=3, >0: 67%, <0: 33%) |
| Magnus Monte Carlsen v4, all 150 | +0.35 (n=149, >0: 27%, <0: 13%) | +0.02 (n=148, >0: 24%, <0: 41%) | -0.28 (n=141, >0: 32%, <0: 42%) | -0.34 (n=136, >0: 38%, <0: 49%) | -0.65 (n=103, >0: 45%, <0: 48%) | -0.13 (n=60, >0: 45%, <0: 43%) |
| MMC v4, 82 wins | +0.63 (n=82, >0: 34%, <0: 11%) | +0.71 (n=82, >0: 35%, <0: 28%) | +1.29 (n=75, >0: 45%, <0: 23%) | +2.09 (n=70, >0: 59%, <0: 26%) | +4.06 (n=51, >0: 76%, <0: 14%) | +4.33 (n=30, >0: 80%, <0: 7%) |
| MMC v4, 64 losses | +0.03 (n=63, >0: 19%, <0: 13%) | -0.84 (n=62, >0: 8%, <0: 56%) | -2.13 (n=62, >0: 16%, <0: 63%) | -3.06 (n=62, >0: 16%, <0: 76%) | -5.60 (n=48, >0: 15%, <0: 81%) | -5.12 (n=26, >0: 12%, <0: 81%) |

**Greek Gift (179 games)**: first ahead in material in 177/179 games; ply of first lead: mean 21, median 18, min 4, max 62; size of that first lead: 1: 104, 2: 22, 3: 40, 4: 1, 5: 4, 7: 1, 8: 1, 9: 4.
- produced by the bot's own capture: 177/177 (rest: promotion or opponent's move)
- captured piece: P: 97, B: 33, N: 32, Q: 8, R: 7; capturing piece: P: 98, B: 32, N: 30, R: 9, Q: 8
- capturer unseen by the victim before the capture: 30/177 (17%)
- capturer unseen, piece captures only (N/B/R/Q): 23/80

**Greek Gift wins**: first ahead in material in 162/163 games; ply of first lead: mean 20, median 18, min 4, max 60; size of that first lead: 1: 92, 2: 21, 3: 38, 4: 1, 5: 4, 7: 1, 8: 1, 9: 4.
- produced by the bot's own capture: 162/162 (rest: promotion or opponent's move)
- captured piece: P: 86, B: 31, N: 30, Q: 8, R: 7; capturing piece: P: 87, B: 29, N: 29, R: 9, Q: 8
- capturer unseen by the victim before the capture: 27/162 (17%)
- capturer unseen, piece captures only (N/B/R/Q): 21/76

**MMC v4 (150 games)**: first ahead in material in 140/150 games; ply of first lead: mean 12, median 8, min 3, max 76; size of that first lead: 1: 97, 2: 18, 3: 14, 4: 2, 6: 1, 7: 3, 8: 3, 9: 2.
- produced by the bot's own capture: 140/140 (rest: promotion or opponent's move)
- captured piece: P: 87, N: 28, Q: 12, B: 11, R: 2; capturing piece: P: 89, N: 23, B: 18, Q: 6, R: 3, K: 1
- capturer unseen by the victim before the capture: 16/140 (11%)
- capturer unseen, piece captures only (N/B/R/Q): 15/53

**MMC v4 wins**: first ahead in material in 82/82 games; ply of first lead: mean 11, median 9, min 3, max 50; size of that first lead: 1: 52, 2: 13, 3: 11, 4: 1, 7: 3, 8: 1, 9: 1.
- produced by the bot's own capture: 82/82 (rest: promotion or opponent's move)
- captured piece: P: 49, N: 20, B: 6, Q: 6, R: 1; capturing piece: P: 51, N: 18, B: 9, R: 3, K: 1
- capturer unseen by the victim before the capture: 9/82 (11%)
- capturer unseen, piece captures only (N/B/R/Q): 8/33

**Greek Gift**: first lead of >= 3 reached in 167/179 games (median ply 29); still >= 3 at the end in 126.
**Greek Gift wins**: first lead of >= 3 reached in 157/163 games (median ply 28); still >= 3 at the end in 125.
**MMC v4**: first lead of >= 3 reached in 116/150 games (median ply 24.5); still >= 3 at the end in 63.

### Captures and unseen captures

A capture is `unseen` when the captured side's view in the frame before the move showed `?` on the capturing piece's square (it could not see the attacker). Values P1 N3 B3 R5 Q9.

| who captures | games | captures | unseen | pawn captures / unseen | piece captures / unseen | value taken per game | value taken unseen per game | unseen capturer piece |
|---|---|---|---|---|---|---|---|---|
| Greek Gift (all 179) | 179 | 1792 (10.0/game) | 727 (41%) | 764 / 312 (41%) | 1028 / 415 (40%) | 29.6 | 10.4 (35%) | N: 193, B: 156, R: 140, Q: 131, P: 80, K: 27 |
| GG's opponents | 179 | 1542 (8.6/game) | 540 (35%) | 656 / 188 (29%) | 886 / 352 (40%) | 25.2 | 7.8 (31%) | B: 130, N: 115, R: 112, Q: 90, P: 51, K: 42 |
| Greek Gift, in its wins | 163 | 1646 (10.1/game) | 670 (41%) | 698 / 285 (41%) | 948 / 385 (41%) | 30.0 | 10.7 (36%) | N: 181, B: 148, R: 130, Q: 115, P: 73, K: 23 |
| GG's opponents, in GG wins | 163 | 1370 (8.4/game) | 467 (34%) | 582 / 160 (27%) | 788 / 307 (39%) | 24.6 | 7.3 (30%) | B: 113, N: 96, R: 94, Q: 80, P: 46, K: 38 |
| Greek Gift, in its losses | 11 | 100 (9.1/game) | 39 (39%) | 48 / 18 (38%) | 52 / 21 (40%) | 24.4 | 7.9 (32%) | R: 9, N: 8, Q: 8, P: 6, B: 5, K: 3 |
| GG's opponents, in GG losses | 11 | 125 (11.4/game) | 56 (45%) | 53 / 21 (40%) | 72 / 35 (49%) | 34.3 | 14.2 (41%) | N: 17, R: 13, B: 11, Q: 8, K: 4, P: 3 |
| Greek Gift vs us | 6 | 64 (10.7/game) | 27 (42%) | 24 / 7 (29%) | 40 / 20 (50%) | 33.7 | 14.2 (42%) | N: 7, Q: 7, B: 4, R: 4, K: 3, P: 2 |
| us vs Greek Gift | 6 | 52 (8.7/game) | 21 (40%) | 19 / 8 (42%) | 33 / 13 (39%) | 26.7 | 8.2 (31%) | B: 7, R: 5, N: 4, K: 2, Q: 2, P: 1 |
| MMC v4 (all 150) | 150 | 1374 (9.2/game) | 583 (42%) | 612 / 269 (44%) | 762 / 314 (41%) | 26.4 | 9.2 (35%) | R: 137, N: 131, B: 119, Q: 110, K: 45, P: 41 |
| MMC's opponents | 150 | 1385 (9.2/game) | 541 (39%) | 593 / 218 (37%) | 792 / 323 (41%) | 27.4 | 9.3 (34%) | N: 125, Q: 117, B: 112, R: 88, P: 70, K: 29 |
| MMC v4, in its wins | 82 | 784 (9.6/game) | 333 (42%) | 359 / 156 (43%) | 425 / 177 (42%) | 27.8 | 9.7 (35%) | R: 81, B: 71, N: 71, Q: 68, P: 22, K: 20 |
| MMC's opponents, in MMC wins | 82 | 666 (8.1/game) | 249 (37%) | 291 / 106 (36%) | 375 / 143 (38%) | 23.8 | 7.4 (31%) | B: 65, N: 57, Q: 41, P: 38, R: 36, K: 12 |
| MMC v4, in its losses | 64 | 550 (8.6/game) | 230 (42%) | 237 / 103 (43%) | 313 / 127 (41%) | 24.4 | 8.3 (34%) | N: 54, R: 53, B: 43, Q: 39, K: 24, P: 17 |
| MMC's opponents, in MMC losses | 64 | 676 (10.6/game) | 280 (41%) | 284 / 109 (38%) | 392 / 171 (44%) | 31.5 | 11.7 (37%) | Q: 71, N: 66, R: 51, B: 46, P: 29, K: 17 |

Unseen share of captures by ply band (captures by the named side / its opponents):

| ply band | GG captures (unseen%) | GG opp captures (unseen%) | MMC captures (unseen%) | MMC opp captures (unseen%) |
|---|---|---|---|---|
| 1-20 | 284 (26%) | 283 (29%) | 308 (24%) | 349 (39%) |
| 21-40 | 522 (39%) | 466 (38%) | 474 (47%) | 458 (35%) |
| 41-60 | 470 (47%) | 388 (35%) | 329 (48%) | 321 (44%) |
| 61-80 | 271 (44%) | 226 (33%) | 159 (45%) | 162 (36%) |
| 81-120 | 187 (40%) | 140 (39%) | 89 (54%) | 76 (47%) |
| 121-400 | 58 (53%) | 39 (36%) | 15 (60%) | 19 (42%) |

Unseen captures by captured piece type (count, and share of all captures of that piece type):

| captured | GG takes | GG loses | MMC takes | MMC loses |
|---|---|---|---|---|
| P | 312/764 (41%) | 188/656 (29%) | 269/612 (44%) | 218/593 (37%) |
| N | 192/312 (62%) | 172/282 (61%) | 143/238 (60%) | 172/252 (68%) |
| B | 119/295 (40%) | 114/263 (43%) | 104/219 (47%) | 73/221 (33%) |
| R | 80/271 (30%) | 62/211 (29%) | 59/192 (31%) | 66/194 (34%) |
| Q | 24/150 (16%) | 4/130 (3%) | 8/113 (7%) | 12/125 (10%) |

## 4. Material lost to unseen attackers, per game

| | games | mean value the bot's opponent loses to unseen attackers | mean value the bot loses to unseen attackers | net | games where opp lost more that way | games where bot lost more |
|---|---|---|---|---|---|---|
| Greek Gift | 179 | 10.40 | 7.78 | +2.62 | 112 | 57 |
| GG wins | 163 | 10.66 | 7.34 | +3.32 | 109 | 45 |
| GG losses | 11 | 7.91 | 14.18 | -6.27 | 1 | 9 |
| GG draws | 5 | 7.20 | 7.80 | -0.60 | 2 | 3 |
| GG vs us | 6 | 14.17 | 8.17 | +6.00 | 5 | 1 |
| MMC v4 | 150 | 9.18 | 9.27 | -0.09 | 66 | 69 |
| MMC wins | 82 | 9.74 | 7.43 | +2.32 | 46 | 26 |
| MMC losses | 64 | 8.34 | 11.69 | -3.34 | 18 | 42 |

Where the material edge at the kill comes from (GG wins): value GG took unseen minus value GG lost unseen, versus value from seen captures.

- mean net from unseen captures: +3.32; mean net from seen captures: +2.07 (promotions not counted; mean material edge before the fatal move +8.37).
- MMC v4, all 150 games: net from unseen captures -0.09, net from seen captures -0.89.

## 3. The 11 losses and 5 draws

| opp | opp ver | colour | plies | kind | attacker | from | GG king | fatal move | material GG-opp at end | 10 plies before | GG clock / opp clock at end |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Farsight | v33 | B | 38 | check_unanswered | R | f8 | h8 | other a5a4 | -16 | -5 | 122s / 148s |
| HYPOTHERMIA | v19 | B | 48 | check_unanswered | R | b7 | e7 | other e8d6 | +0 | +0 | 68s / 91s |
| Crimson Fog | v4 | B | 70 | check_unanswered | Q | g7 | f8 | king_move e7f8 | -9 | -11 | 34s / 124s |
| duck | v11 | W | 81 | walked_in | Q | h5 | h1 | king_move g1h1 | -17 | -11 | 15s / 47s |
| Decent Chess Bot | v7 | W | 83 | check_unanswered | Q | h6 | h3 | king_move g2h3 | -16 | -14 | 29s / 40s |
| Crimson Fog | v4 | W | 105 | walked_in | Q | e5 | h2 | other g3g4 | -9 | -7 | 13s / 108s |
| Strongly Invisible | v42 | W | 109 | check_unanswered | N | d3 | f2 | king_move g2f2 | -20 | -9 | 13s / 64s |
| duck | v11 | B | 114 | check_unanswered | Q | h4 | g5 | king_move h6g5 | -14 | -13 | 13s / 50s |
| Gravel Road | v13 | B | 126 | walked_in | R | e1 | e8 | king_move f8e8 | -9 | -7 | 13s / 20s |
| Foggy Fischer | v6 | B | 134 | walked_in | N | f4 | h3 | king_move h4h3 | +1 | +0 | 12s / 68s |
| Cranberry Lemon | v9 | B | 136 | check_unanswered | R | f7 | c7 | other h2h1 | -8 | -7 | 12s / 12s |

Draws (all threefold repetition):

| opp | opp ver | colour | plies | material GG-opp at end | GG clock / opp clock | last 6 moves |
|---|---|---|---|---|---|---|
| Strongly Invisible | v42 | B | 154 | +1 | 12s / 51s | d8d1 f6g6 d1d8 g6h5 d8d1 h5g6 |
| HYPOTHERMIA | v19 | B | 113 | +0 | 13s / 41s | e7g6 g2f2 h6h7 f2g2 h7h6 g2f2 |
| Next | v8 | W | 175 | +0 | 12s / 16s | g8h7 e4d3 h7g8 d3e2 g8h7 e2f3 |
| RATIRL | v2 | B | 63 | +6 | 35s / 131s | g7f7 e6g4 f7g7 g4e6 g7f7 e6g4 |
| Strongly Invisible | v42 | B | 88 | -2 | 14s / 85s | h2g3 e4e6 g3h2 e6e8 h2g3 e8e6 |

Loss details (material GG-opp every 10 plies, then the last 8 moves with the mover):

- **Farsight** (B, 38 plies): material 10:+0 20:+0 30:-8; end -16. Last moves: op:Nd7b8 GG:Ra8b8x op:Rd8b8x GG:Bb7c8 op:Rb8c8x GG:Pa7a5 op:Rc8f8x GG:Pa5a4. GG saw attacker before fatal move: False; attacker R on f8 at distance 2, line=0.
- **HYPOTHERMIA** (B, 48 plies): material 10:+0 20:+0 30:+0 40:+0; end +0. Last moves: op:Rd3a3 GG:Rb8b6 op:Rd1d3 GG:Rb6a6 op:Rd3b3 GG:Nf6e8 op:Rb3b7 GG:Ne8d6. GG saw attacker before fatal move: False; attacker R on b7 at distance 3, line=0.
- **Crimson Fog** (B, 70 plies): material 10:+0 20:+0 30:+0 40:-7 50:-10 60:-11 70:-9; end -9. Last moves: op:Kd2c1 GG:Pc6c5 op:Rh4f4 GG:Kf7e7 op:Rf4f6x GG:Re6f6x op:Qg5g7 GG:Ke7f8. GG saw attacker before fatal move: False; attacker Q on g7 at distance 1, line=0.
- **duck** (W, 81 plies): material 10:+0 20:+0 30:+0 40:-3 50:-3 60:-6 70:-11 80:-17; end -17. Last moves: op:Qf7h5 GG:Pe3e4 op:Rd7e7 GG:Bf4e3 op:Re7e4x GG:Pb4a5x op:Re4e3x GG:Kg1h1. GG saw attacker before fatal move: False; attacker Q on h5 at distance 4, line=6.
- **Decent Chess Bot** (W, 83 plies): material 10:+0 20:+0 30:-2 40:-4 50:-9 60:-10 70:-13 80:-15; end -16. Last moves: op:Kg8f7 GG:Pf5f6 op:Qc6c1 GG:Kg1g2 op:Qc1h6 GG:Pf2f3 op:Pg4f3x GG:Kg2h3. GG saw attacker before fatal move: False; attacker Q on h6 at distance 3, line=2.
- **Crimson Fog** (W, 105 plies): material 10:+1 20:+1 30:+3 40:+3 50:+1 60:+1 70:-8 80:+1 90:+1 100:-7; end -9. Last moves: op:Qf5e5 GG:Kg2h2 op:Ke8e7 GG:Pd5d6 op:Ke7e6x GG:Pd6d7 op:Ke6d7x GG:Pg3g4. GG saw attacker before fatal move: False; attacker Q on e5 at distance 3, line=0.
- **Strongly Invisible** (W, 109 plies): material 10:+0 20:+0 30:-2 40:-6 50:-12 60:-12 70:-12 80:-12 90:-12 100:-9; end -20. Last moves: op:Nd7e5 GG:Bc3e1 op:Ne5d3 GG:Be1g3 op:Ne4g3x GG:Kh1g2 op:Ph2h1q GG:Kg2f2. GG saw attacker before fatal move: False; attacker N on d3 at distance 2, line=4.
- **duck** (B, 114 plies): material 10:+0 20:+3 30:+0 40:+0 50:-2 60:-1 70:-2 80:-5 90:-5 100:-4 110:-14; end -14. Last moves: op:Qb3f7x GG:Kg7h6 op:Qf7f8 GG:Kh6g5 op:Qf8f6 GG:Kg5h6 op:Qf6h4 GG:Kh6g5. GG saw attacker before fatal move: False; attacker Q on h4 at distance 1, line=0.
- **Gravel Road** (B, 126 plies): material 10:+0 20:-1 30:-3 40:-4 50:-4 60:-5 70:-8 80:-4 90:-7 100:-7 110:-6 120:-8; end -9. Last moves: op:Re3g3x GG:Kg7f8 op:Rg3g1 GG:Pf7f6 op:Rg1e1 GG:Pf6f5 op:Bb1f5x GG:Kf8e8. GG saw attacker before fatal move: False; attacker R on e1 at distance 7, line=2.
- **Foggy Fischer** (B, 134 plies): material 10:+0 20:+2 30:+0 40:+0 50:+0 60:+0 70:+0 80:+0 90:+0 100:+0 110:-1 120:-1 130:+0; end +1. Last moves: op:Nb3c1 GG:Ke5f4 op:Kc3d2 GG:Kf4g4 op:Nc1e2 GG:Kg4h4x op:Ne2f4 GG:Kh4h3. GG saw attacker before fatal move: False; attacker N on f4 at distance 2, line=0.
- **Cranberry Lemon** (B, 136 plies): material 10:+0 20:+0 30:+1 40:+1 50:+1 60:+1 70:+2 80:+2 90:+2 100:-3 110:-6 120:-6 130:-8; end -8. Last moves: op:Bd2g5x GG:Ra4a2 op:Ph6h7 GG:Pf7f5 op:Rd6f6 GG:Ra2h2 op:Rf6f7 GG:Rh2h1. GG saw attacker before fatal move: False; attacker R on f7 at distance 3, line=0.

Losers' opponents: Crimson Fog: 2, duck: 2, Cranberry Lemon: 1, Decent Chess Bot: 1, Farsight: 1, Foggy Fischer: 1, Gravel Road: 1, HYPOTHERMIA: 1, Strongly Invisible: 1. Draw opponents: Strongly Invisible: 2, HYPOTHERMIA: 1, Next: 1, RATIRL: 1.
Losses by colour: B: 7, W: 4. Loss kill kinds: check_unanswered: 7, walked_in: 4; attacker: Q: 5, R: 4, N: 2; GG's fatal move: king_move: 7, other: 4.
Material GG-opp before the fatal move in losses: [-20, -17, -16, -16, -14, -9, -9, -9, -8, 0, 1].
## Clocks (180 s + 2 s)

Mean clock (seconds left) after N plies, games lasting at least N plies.

| games | ply 20 | ply 40 | ply 60 | ply 80 | ply 100 | ply 120 | at end |
|---|---|---|---|---|---|---|---|
| Greek Gift, all | 137 (n=179) | 88 (n=171) | 49 (n=139) | 24 (n=104) | 15 (n=62) | 13 (n=34) | 37, min 12 |
| GG's opponents | 147 (n=179) | 115 (n=171) | 89 (n=139) | 70 (n=104) | 59 (n=62) | 52 (n=34) | 80, min 8 |
| GG in wins | 136 (n=163) | 88 (n=156) | 49 (n=125) | 24 (n=92) | 15 (n=53) | 12 (n=29) | 38, min 12 |
| GG in losses | 136 (n=11) | 86 (n=10) | 52 (n=9) | 26 (n=8) | 16 (n=6) | 13 (n=3) | 31, min 12 |
| opp in GG losses | 139 (n=11) | 103 (n=10) | 82 (n=9) | 61 (n=8) | 57 (n=6) | 36 (n=3) | 70, min 12 |
| GG in draws | 142 (n=5) | 89 (n=5) | 46 (n=5) | 19 (n=4) | 13 (n=3) | 12 (n=2) | 17, min 12 |
| MMC v4 | 146 (n=148) | 115 (n=136) | 90 (n=103) | 71 (n=60) | 58 (n=35) | 49 (n=20) | 84, min 19 |
| MMC's opponents | 154 (n=148) | 122 (n=136) | 104 (n=103) | 83 (n=60) | 69 (n=35) | 76 (n=20) | 103, min 3 |

Seconds per move by ply band (mean; clock difference plus the 2 s increment).

| who | 1-20 | 21-40 | 41-60 | 61-80 | 81-100 | 101-140 | >140 |
|---|---|---|---|---|---|---|---|
| Greek Gift | 6.34 (n=1790) | 6.76 (n=1777) | 5.68 (n=1543) | 4.40 (n=1184) | 2.93 (n=805) | 2.18 (n=714) | 2.00 (n=297) |
| GG's opponents | 5.33 (n=1790) | 5.19 (n=1778) | 4.14 (n=1551) | 3.44 (n=1201) | 3.00 (n=825) | 2.48 (n=736) | 2.00 (n=304) |
| MMC v4 | 5.38 (n=1494) | 5.04 (n=1406) | 4.42 (n=1188) | 3.79 (n=793) | 3.16 (n=474) | 2.70 (n=371) | 1.94 (n=132) |
| MMC's opponents | 4.65 (n=1492) | 4.83 (n=1412) | 3.79 (n=1193) | 3.24 (n=788) | 2.83 (n=473) | 2.20 (n=374) | 2.31 (n=133) |

Games where Greek Gift's clock fell below 20 s at some point, by outcome: {('win', False): 84, ('win', True): 79, ('draw', True): 4, ('loss', True): 7, ('loss', False): 4, ('draw', False): 1}
Same for its opponents' clocks: {('win', False): 149, ('draw', False): 4, ('loss', False): 9, ('win', True): 14, ('loss', True): 2, ('draw', True): 1}

Games where GG's clock went under 20 s: 90; mean ply when it happened 82; material change from that ply to the end: mean +3.33; outcomes {'win': 79, 'draw': 4, 'loss': 7}.

## Promotions

| | games | promotions by the bot | by its opponent |
|---|---|---|---|
| Greek Gift | 179 | 37 (0.21/game) | 7 (0.04/game) |
| GG wins | 163 | 36 (0.22/game) | 5 (0.03/game) |
| GG losses | 11 | 1 (0.09/game) | 2 (0.18/game) |
| MMC v4 | 150 | 41 (0.27/game) | 13 (0.09/game) |

## Captures worth >= 3 against Greek Gift in its 11 losses

| opp | ply | GG lost | taken by | unseen | GG clock then | material GG-opp after |
|---|---|---|---|---|---|---|
| Farsight | 17 | N | N | no | 158s | -3 |
| Farsight | 19 | Q | Q | no | 150s | -9 |
| Farsight | 21 | R | R | no | 146s | -5 |
| Farsight | 29 | N | N | no | 130s | -8 |
| Farsight | 33 | R | R | no | 122s | -10 |
| Farsight | 35 | B | R | yes | 118s | -13 |
| Farsight | 37 | B | R | yes | 120s | -16 |
| HYPOTHERMIA | 9 | B | B | no | 163s | -3 |
| HYPOTHERMIA | 17 | Q | N | yes | 147s | +0 |
| HYPOTHERMIA | 31 | N | N | no | 109s | -3 |
| HYPOTHERMIA | 33 | B | B | no | 103s | -3 |
| Crimson Fog | 27 | N | B | yes | 102s | -3 |
| Crimson Fog | 29 | B | N | yes | 99s | -3 |
| Crimson Fog | 37 | Q | Q | no | 83s | -8 |
| Crimson Fog | 43 | R | K | no | 75s | -9 |
| Crimson Fog | 47 | B | N | no | 69s | -13 |
| Crimson Fog | 67 | N | R | yes | 42s | -14 |
| duck | 40 | N | N | no | 77s | -3 |
| duck | 48 | Q | R | no | 58s | -7 |
| duck | 60 | R | B | yes | 35s | -6 |
| duck | 62 | N | P | yes | 32s | -6 |
| duck | 68 | R | B | yes | 24s | -11 |
| duck | 72 | B | Q | yes | 20s | -14 |
| duck | 80 | B | R | yes | 16s | -17 |
| Decent Chess Bot | 18 | B | N | yes | 140s | -3 |
| Decent Chess Bot | 28 | N | P | yes | 113s | -3 |
| Decent Chess Bot | 38 | R | B | yes | 97s | -7 |
| Decent Chess Bot | 42 | Q | Q | no | 90s | -8 |
| Decent Chess Bot | 58 | N | R | yes | 64s | -12 |
| Decent Chess Bot | 60 | B | Q | no | 61s | -10 |
| Decent Chess Bot | 64 | R | Q | no | 56s | -12 |
| Crimson Fog | 14 | B | N | yes | 151s | -1 |
| Crimson Fog | 28 | N | R | yes | 116s | -2 |
| Crimson Fog | 32 | B | P | no | 103s | +3 |
| Crimson Fog | 46 | R | R | no | 66s | +1 |
| Crimson Fog | 52 | N | P | yes | 57s | +1 |
| Crimson Fog | 70 | Q | Q | no | 30s | -8 |
| Crimson Fog | 74 | R | R | no | 27s | -4 |
| Strongly Invisible | 26 | N | K | yes | 125s | -2 |
| Strongly Invisible | 36 | R | B | yes | 101s | -6 |
| Strongly Invisible | 38 | B | B | no | 98s | -9 |
| Strongly Invisible | 44 | Q | N | yes | 86s | -8 |
| Strongly Invisible | 48 | N | K | yes | 80s | -12 |
| Strongly Invisible | 94 | R | K | yes | 14s | -9 |
| Strongly Invisible | 106 | B | N | yes | 13s | -12 |
| duck | 21 | N | B | yes | 130s | +0 |
| duck | 25 | N | Q | yes | 123s | +0 |
| duck | 49 | R | B | yes | 61s | -2 |
| duck | 57 | B | Q | no | 48s | -4 |
| duck | 69 | R | Q | yes | 30s | -2 |
| duck | 79 | B | Q | no | 23s | -5 |
| duck | 103 | Q | Q | no | 14s | -13 |
| Gravel Road | 11 | B | Q | no | 165s | -3 |
| Gravel Road | 23 | B | N | yes | 137s | -4 |
| Gravel Road | 33 | R | R | no | 112s | -8 |
| Gravel Road | 45 | N | N | no | 91s | -4 |
| Gravel Road | 61 | R | N | yes | 66s | -10 |
| Gravel Road | 63 | Q | K | no | 63s | -8 |
| Gravel Road | 87 | N | R | no | 32s | -7 |
| Gravel Road | 109 | Q | Q | no | 16s | -15 |
| Foggy Fischer | 13 | N | N | no | 161s | -3 |
| Foggy Fischer | 21 | B | P | no | 144s | -1 |
| Foggy Fischer | 33 | Q | R | no | 117s | +0 |
| Foggy Fischer | 41 | R | R | no | 95s | -5 |
| Foggy Fischer | 45 | R | N | yes | 86s | +0 |
| Foggy Fischer | 47 | N | B | yes | 82s | -3 |
| Cranberry Lemon | 25 | N | B | no | 115s | +0 |
| Cranberry Lemon | 27 | B | R | yes | 109s | +0 |
| Cranberry Lemon | 29 | Q | Q | no | 103s | -8 |
| Cranberry Lemon | 47 | B | N | yes | 63s | -2 |
| Cranberry Lemon | 97 | R | R | no | 13s | -3 |
| Cranberry Lemon | 103 | N | R | yes | 13s | -6 |

## How GG's opponents in the losses first got ahead

- Farsight (B): first behind at ply 15 (-1), opponent's P took GG's P, capturer seen by GG; moves: op:Pd4e5x GG:Nc6e5x op:Nf3e5x GG:Pd6e5x; GG clock 165s
- HYPOTHERMIA (B): first behind at ply 9 (-3), opponent's B took GG's B, capturer seen by GG; moves: op:Bf4d6x GG:Qd8d6x op:Pe2e4 GG:Pd5e4x; GG clock 163s
- Crimson Fog (B): first behind at ply 27 (-3), opponent's B took GG's N, capturer unseen by GG; moves: op:Bf4c7x GG:Qd8c7x op:Ng5e6x GG:Pf7e6x; GG clock 102s
- duck (W): first behind at ply 40 (-3), opponent's N took GG's N, capturer seen by GG; moves: op:Nd7e5x GG:Pf4e5x op:Re8f8 GG:Ph3h4; GG clock 77s
- Decent Chess Bot (W): first behind at ply 18 (-3), opponent's N took GG's B, capturer unseen by GG; moves: op:Ng6f4x GG:Pe3f4x op:Nc6e7 GG:Rf1e1; GG clock 140s
- Crimson Fog (W): first behind at ply 14 (-1), opponent's N took GG's B, capturer unseen by GG; moves: op:Nc6e5x GG:Nf3e5x op:Bf8c5x GG:Ne5d3; GG clock 151s
- Strongly Invisible (W): first behind at ply 26 (-2), opponent's K took GG's N, capturer unseen by GG; moves: op:Ke7e6x GG:Pa2a3 op:Ke6e7 GG:Pa3b4x; GG clock 125s
- duck (B): first behind at ply 41 (-1), opponent's P took GG's P, capturer seen by GG; moves: op:Pa4b5x GG:Pa6b5x op:Pf2f3 GG:Pb5b4; GG clock 81s
- Gravel Road (B): first behind at ply 5 (-1), opponent's P took GG's P, capturer seen by GG; moves: op:Pc4d5x GG:Pc6d5x op:Qd1c2 GG:Nb8c6; GG clock 172s
- Foggy Fischer (B): first behind at ply 11 (-1), opponent's P took GG's P, capturer seen by GG; moves: op:Pc4d5x GG:Nf6d5x op:Nc3d5x GG:Qd8d5x; GG clock 159s
- Cranberry Lemon (B): first behind at ply 19 (-1), opponent's P took GG's P, capturer seen by GG; moves: op:Pd4c5x GG:Pb6c5x op:Pe3e4 GG:Pd5e4x; GG clock 134s

Ratings of the bots that beat or drew Greek Gift (current leaderboard):
- loss: Strongly Invisible 2014.9449759566244
- loss: Farsight 2030.2244924683675
- loss: Crimson Fog 1958.327464899266
- loss: Foggy Fischer 1936.4929154043673
- loss: Gravel Road 1904.707525975278
- loss: Decent Chess Bot 1969.8378883979717
- loss: Crimson Fog 1958.327464899266
- loss: duck 1943.1307838914645
- loss: HYPOTHERMIA 1953.9120779659431
- loss: Cranberry Lemon 1849.4663126299254
- loss: duck 1943.1307838914645
- draw: Strongly Invisible 2014.9449759566244
- draw: HYPOTHERMIA 1953.9120779659431
- draw: Next 1950.3269351654487
- draw: RATIRL 1738.2821926282509
- draw: Strongly Invisible 2014.9449759566244

## In the 104 check_unanswered wins: could the loser have escaped?

{'no safe move (mate)': 44, 'had a safe move': 60} (safe move = any FoW-legal move after which the king is not attacked on the true board).
GG's own check_unanswered losses: {('Strongly Invisible', 'mate'): 1, ('Farsight', 'mate'): 1, ('Crimson Fog', 'safe'): 1, ('Decent Chess Bot', 'safe'): 1, ('duck', 'mate'): 1, ('HYPOTHERMIA', 'safe'): 1, ('Cranberry Lemon', 'safe'): 1}

## From material edge to kill (GG wins)

Wins where GG reached >= +6: 134/163; plies from first reaching +6 to the kill: mean 39, median 27, max 167.
Wins where GG reached >= +3: 157/163; plies from first reaching +3 to the kill: mean 61, median 55, max 297.
MMC v4 wins where it reached >= +3: 77/82; plies from +3 to the kill: mean 52, median 49.
Non-wins where GG had been >= +3 at some point: 10: Strongly Invisible (draw, max +3); Foggy Fischer (loss, max +9); Crimson Fog (loss, max +6); duck (loss, max +3); HYPOTHERMIA (draw, max +5); HYPOTHERMIA (loss, max +9); Cranberry Lemon (loss, max +3); Next (draw, max +4); RATIRL (draw, max +6); Strongly Invisible (draw, max +4)

## The winner's last move before the fatal ply (GG wins)

| kill kind | piece moved | capture? | n |
|---|---|---|---|
| check_unanswered | Q | quiet | 43 |
| check_unanswered | R | quiet | 23 |
| check_unanswered | Q | capture | 14 |
| walked_in | R | quiet | 11 |
| walked_in | P | quiet | 11 |
| walked_in | Q | quiet | 10 |
| walked_in | K | quiet | 10 |
| check_unanswered | R | capture | 9 |
| check_unanswered | P | quiet | 6 |
| walked_in | B | quiet | 6 |
| check_unanswered | N | quiet | 5 |
| walked_in | P | capture | 3 |
| walked_in | R | capture | 2 |
| walked_in | N | quiet | 2 |
| walked_in | Q | capture | 2 |
| check_unanswered | B | capture | 1 |
| walked_in | N | capture | 1 |
| walked_in | B | capture | 1 |
| check_unanswered | B | quiet | 1 |
| check_unanswered | N | capture | 1 |
| check_unanswered | P | capture | 1 |
