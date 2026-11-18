# Greek Gift: what the 2302 bot does that the pool does not

Study of 2026-11-18. Greek Gift (v30) is rated 2302; the next bot is 2034, we are 1871
(14th of 43). Its current version is 163-5-11 in 179 games; 6-0 against us. All 179
replays were pulled from the public API and compared with our 150 arena games (v4).
The five full reports with every table are in `docs/greek-gift/` (openings, kills, style,
time, king). The numbers that matter:

**Not the opening.** 1.d4 every game (Exchange QGD or London; Staunton gambit against
1...f5); as black ...c6/...d5 or ...Nf6/...g6. No early queen raids: the queen's first move
comes at ply 26 on median, no game ends before ply 30. Vision over the first 20 plies is the
same as ours (37.1 vs 37.3 squares). Common-opponent score 0.93 vs our 0.52, so the pool
is not the difference either.

**Not Stockfish-likeness.** Top-1 agreement with true-board Stockfish 33% (ours 37%; in
the opening 37% vs our 50%). Its deviations are cheaper (31 cp vs 42) and go away from
captures, checks and squares attacked from the fog; ours go towards attacked squares.

**Material, then a hunt.** +0.1 at ply 20, +1.0 at 30, +1.8 at 40, +3.4 at 60; +8.4 before
the kill, only 7% of wins from an even position. Captures by a piece the victim could not
see: 10.4 points per game taken, 7.8 lost (net +2.6). Ours: 9.2 taken, 9.3 lost (net 0).
It leaves 3+ points en prise on 5.9% of moves (ours 9.0%); its queen is gone by ply 40 in
21% of games (ours 41%). After its moves 1.47 points of its material stand on squares
attacked from the fog (ours 1.88; plies 21-40: 2.02 vs 2.72). Undefended quiet pieces hung
into the fog: 4 in 2,704 moves (ours 16 in 1,627).

**Vision.** After its move it sees 3.5 squares more than its opponent, 4.9 after ply 40.
We see 0.3 more early and 0.4 fewer late.

**The king.** King moves 10.4% of all moves (opponents 17.9%, us 15.3%); with 0 pieces
left 50% (us 67%). Castles in 93% of games at ply 17; the king is on g1/h1/g2/h2 at ply 60
in 76% of games. Its king steps onto an attacked square in 1.1% of king moves (opponents
7.7%, us 6.1%); it walks into a standing unseen line 3 times in 179 games (we did 35 times
in 64 losses). Its king is attacked by an unseen piece on 2 plies in 60 games (ours 15 in
40). Against an unseen check it interposes 51% of the time at normal think time, with the
attacker's origin visible in only 5 of 23 cases: its belief contains the checking piece.

**The actual Greek gift.** In 40 of 163 wins its last move hangs a queen or rook on a
square the loser attacks; the loser takes it and a hidden piece takes the king (27 times by
a pinned or exposed capture, 14 times the king itself recaptured). Engine-on-belief bots
fall for it because their sampled boards do not hold the protector.

**Clock.** 5.2 s a move; think = 2 + (clock - 12) / max(6, 40.75 - 0.75 n) to within
0.02 s; it drains the clock to a 12 s reserve and plays on the increment after that. 90 of
179 games end under 20 s, and those hold all 5 draws and 7 of 11 losses. We end with 84 s
unused. It is not deterministic in its moves (identical views give different replies in
20-30% of cases) but its timing is.

**Its losses.** 11, all to bots rated 1849-2030, 9 of them from 8-20 points down; the fatal
move was a king step onto an attacked square in 7 (a safe square existed in 5).
