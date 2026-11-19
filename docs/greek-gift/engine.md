# Greek Gift v30: is it Stockfish on sampled boards?

Data: all 179 arena games of Greek Gift v30 in `gg_games.pkl` (8,110 of its decisions).
Engine: the eBotI Stockfish build, 1 thread, 64 MB hash, fresh `ucinewgame` per position.
Scripts and outputs live in `gg2/engine/` (`extract.py` rows, `infoset.py` information sets,
`sf_run.py` engine cache, `analyze_t1*.py` / `t1.md` / `t1b.md`, `analyze_t2.py` / `t2.md`,
`analyze_t4.py` / `t4.md`, `analyze_sets.py` / `sets.md`, `groups.py` / `groups.md`).

## Method notes that matter

* **"Fully known" cannot be read off the view.** By the rules a pawn reveals only its push
  squares and *occupied* capture squares, so White sees no Black piece at ply 1 although the
  board is known. I therefore enumerated Greek Gift's *information set*: every board consistent
  with the start position, its own moves and all its views (both after its own move and after
  the opponent's), capped at 2,000 boards per decision. 1,906 decisions could be tracked before
  the cap; 277 have exactly one consistent board (fully known), 493 have at most 10, 1,099 at
  most 60. The 277 known positions are mostly book (90 are the start position, 44 are
  1.d4 d5), so I report the 89 at ply 9 or later separately.
* Belief boards for Test 2: (b) "last-seen" = own pieces + visible enemy pieces + each unseen
  square's last observed enemy piece, capped per piece type to the material Greek Gift knows
  the opponent has (from its own captures); (c) "removed" = visible enemy pieces only (the
  enemy king kept at its last seen square). Boards Stockfish rejects (side not to move in
  check, impossible material) are skipped.
* Test 2 ran Stockfish depth 10 MultiPV 5 on a random 3,531-decision sample (of 8,110; the
  run was stopped at that size for time). Information-set members were scored at depth 6.

## Test 1: fully-known positions

All 277 known decisions (110 distinct positions), MultiPV 5:

| limit | top-1 (decisions) | top-3 | top-1 (distinct positions) | rank 1/2/3/4/5/>5 |
|---|---|---|---|---|
| depth 2 | 66% | 83% | 55% | 183/32/15/4/4/39 |
| depth 4 | 40% | 79% | 59% | 110/98/10/31/8/20 |
| depth 6 | 41% | 83% | 56% | 113/16/102/25/3/18 |
| depth 8 | 35% | 82% | 62% | 98/100/30/28/0/21 |
| depth 10 | 34% | 82% | 60% | 94/126/6/11/27/13 |
| depth 12 | 32% | 82% | 54% | 88/131/9/28/9/12 |
| depth 15 | 40% | 91% | 55% | 111/18/122/8/2/16 |
| time 0.5 s | 40% | 84% | 56% | 112/112/10/27/3/13 |
| time 2 s | 42% | 91% | 59% | 116/107/29/10/1/14 |
| time 5 s | 66% | 90% | 59% | 182/36/32/11/4/12 |

The per-decision column is an artefact of two book positions: 1.d4 (90 decisions) is
Stockfish's top move only at depth 2 and at 5 s (tied with Nf3), which is the whole
66%/34% swing. The informative subset is the 89 non-book known decisions (ply >= 9, 87
distinct positions):

| limit | top-1 | top-2 | top-3 | median / mean cp loss when not top-1 | n with gap > 50 cp | > 100 cp |
|---|---|---|---|---|---|---|
| depth 2 | 58% | 70% | 80% | 77 / 105 | 15 | 9 |
| depth 4 | 63% | 71% | 74% | 48 / 95 | 7 | 3 |
| depth 6 | 58% | 72% | 79% | 54 / 105 | 12 | 6 |
| depth 8 | 63% | 72% | 79% | 20 / 50 | 5 | 4 |
| depth 10 | 62% | 75% | 81% | 20 / 37 | 6 | 2 |
| depth 12 | 55% | 73% | 81% | 19 / 304 | 4 | 3 |
| depth 15 | 55% | 72% | 82% | 14 / 35 | 9 | 3 |
| time 0.5 s | 56% | 79% | 83% | 15 / 313 | 7 | 4 |
| time 2 s | 62% | 76% | 82% | 26 / 36 | 7 | 2 |
| time 5 s | 60% | 73% | 82% | 18 / 45 | 8 | 7 |

Reading: agreement is **flat at 55-63% from depth 4 to depth 15 and from 0.5 s to 5 s**.
There is no peak, so no depth can be read off. A bot that ran this Stockfish at depth D on a
known board would agree ~100% at D (minus multithread noise); Greek Gift does not. Its moves
are engine-like (top-3 ~80%, median loss 15-25 cp when it deviates) but chosen by something
other than Stockfish's top line. In the 89 decisions it deviates by more than 100 cp 2-7
times depending on the limit, e.g. ply 19 Bb5 instead of Qh5 (105 cp, in two different games
reaching the same position; both chose Bb5), ply 9 Bg3 (131 cp).

Non-determinism is not belief sampling: two games (`c8293x21`, `0fk2j5gy`) reach the
identical fully-known position at plies 17, 19 and 21; the choices agree at 17 and 19 and
differ at 21 (Bf4, rank 2/>5/5, vs Qh5, rank >5/2/3 depending on limit). With one consistent
board there is nothing to sample; the randomness is in the move choice itself (a timed
search, or random tie-breaking).

## Test 4 first (it decides the sampling question): repeated information states

Grouping decisions by Greek Gift's complete information state (all views and own moves so
far), 49 states occur 4+ times, covering 673 decisions; 103 (15%) are not the state's modal
move. The splits with a known board, against Stockfish:

| state | Greek Gift | Stockfish MultiPV (cp, mover POV) |
|---|---|---|
| start, n=90 | d4 90 | d6: e4 +20, Nf3 +17, **d4 +16**; d15: e4 +32, Nf3 +21, d4 +20; 5 s: d4 +31, Nf3 +31, e4 +27 |
| 1.d4 d5, n=44 | c4 23, Bf4 21, **Nf3 0** | d6: c4 +18, Nf3 +15, e3 +14, Bf4 +13; d15: c4 +26, Nf3 +20, Bf4 +9; 5 s: Nf3 +24, c4 +22, Bf4 +12 |
| 1.d4 c5, n=13 | d5 13 | d5 top by 20-57 cp at every limit |
| 1.d4 c6 2.c4 d5 3.cxd5, n=10 | cxd5 9, Bd7 1 | cxd5 top by 40-90 cp; Bd7 is -113 cp (rank 5 at d6, unlisted deeper) |

Softmax fit, P(move) proportional to exp(cp/T) over the MultiPV-5 list (unlisted moves 1%),
pooled over these four states (157 decisions): best T = 8-30 cp with log-likelihood -1.1 to
-1.5 per decision, which is poor: at T = 10 the start position gives d4 only ~22% (observed
100%), and after 1.d4 d5 every T gives Nf3 at least the probability of Bf4 (observed 0 vs 21
of 44; binomial probability of that split under any softmax over these evals is below 1e-6).
Deterministic Stockfish is worse still (it plays e4 and Nf3). **No Stockfish temperature
reproduces the opening splits.** The 50/50 c4/Bf4 split with Nf3 absent is a weighted book,
not sampling.

States with several consistent boards, model "sample a board, play its Stockfish top-1"
(depth 6 on every member board):

| state | boards | Greek Gift | per-board SF top-1 shares | best mean-cp move over boards |
|---|---|---|---|---|
| Black move 1 (no information) | 20 | c6 47, Nf6 32, c5 3, e6 2, g6 2, Nc6 2, d5 1 | **e5 55%**, d5 25%, Nf6 10%, e6 5%, c5 5% | d5 |
| 1.d4, view unchanged | 14 | Nc3 31, e4 1, c4 1 | **e4 64%**, others 7% each | c4 |
| 1.d4 d5 2.c4 e6 3.cxd5 exd5 | 2 | Bf4 15 | Nc3 100% | Nc3 |
| 1.d4 d5 2.c4 (d5 pawn seen), ply 5 | 19 | cxd5 22, Nc3 1 | cxd5 95% | cxd5 |
| ply 5 state A | 18 | e3 14, c4 2, Nf3 1 | c4 39%, e3 17% | **e3** |
| ply 5 state B | 13 | Nc3 11 | e4 54% | **Nc3** |
| ply 5 state C | 13 | Bf4 10 | e4 77%, Bf4 23% | **Bf4** |
| ply 7 (vs ...f5) | 10 | f3 6 | Ne4 70% | **f3** |
| ply 8 black | 22 | Nc6 9 | Nc6 36% | **Nc6** |
| ply 13 | 12 | Ne2 4, Bf4 1 | Ne2 58% | **Ne2** |
| ply 11 | 30 | Nc3 9 | Bd3 33%, Nf3 30%, Nc3 17% | Nf3 |
| ply 4 black (Nf6 played, white unseen) | 24 | c5 3, d6 2 | Nxe4 75%, e5 21% | Nxe4 (GG never grabs the pawn) |

Black's first move is the cleanest test of board sampling: with zero information, sampling a
board and playing its top-1 would give e5 55% and d5 25%; Greek Gift played e5 0 times and
d5 once in 89 games, and c6, its favourite (53%), is in Stockfish's top 5 on only 8 of the 20
boards. The same holds for 2.Nc3 after an uninformative reply (31/33; sampling predicts e4
64%). These are book moves. Beyond the book (ply >= 5) the repeated states are nearly
deterministic (modal share about 90%), and the modal move equals the **best mean evaluation
over the consistent boards** in 8 of 15 states, including four where the per-board plurality
is a different move (e3, Nc3, Bf4, f3 above). It never equals a per-board plurality that the
mean does not also pick.

## Test 2: uncertain positions, which board explains the moves

Depth 10, MultiPV 5, 3,531 decisions with at least one hidden enemy piece:

| hidden enemy pieces | n | (a) true top-1 / top-3 | (b) last-seen top-1 / top-3 | (c) removed top-1 / top-3 | random top-1 |
|---|---|---|---|---|---|
| 1-2 | 45 | 31% / 60% | 27% / 47% | 16% / 38% | 6% |
| 3-4 | 246 | 30% / 51% | 18% / 41% | 15% / 37% | 5% |
| 5-7 | 805 | 31% / 54% | 19% / 36% | 15% / 30% | 4% |
| 8-11 | 1042 | 34% / 61% | 19% / 36% | 12% / 26% | 3% |
| 12-16 | 1393 | 35% / 71% | 14% / 48% | 6% / 26% | 3% |
| all | 3531 | **33% / 63%** | 17% / 41% | 11% / 28% | 4% |

Where the true-board and last-seen top moves differ (n = 2,771) Greek Gift plays the
true-board move 28% of the time and the last-seen move 7%; versus the removed board, 31% vs
5%. By phase, true-board top-1 is 29% (plies 1-10, book), 44% (11-20), 39% (21-40), 34%
(41-60), 28% (61+). The real position predicts its moves twice as well as a memory of
last-seen squares at every level of uncertainty, so whatever it uses is much better than a
last-seen board, i.e. it reasons about where the hidden pieces can be.

Information-set models on a random sample of 354 decisions with 2-60 consistent boards, every
member scored at depth 6:

| set size | n | true top-1 | last-seen top-1 | plurality of per-board top-1 | best mean cp | best worst-case cp | GG move is top-1 of some board | mean P(GG move) if a board were sampled |
|---|---|---|---|---|---|---|---|---|
| 2-5 | 59 | 41% | 10% | 41% | 41% | 34% | 63% | 0.40 |
| 6-15 | 95 | 44% | 24% | 36% | 44% | 46% | 89% | 0.32 |
| 16-30 | 157 | 25% | 27% | 34% | 36% | 34% | 75% | 0.29 |
| 31-60 | 43 | 40% | 12% | 37% | 35% | 47% | 95% | 0.29 |
| all | 354 | 34% | 21% | 36% | **39%** | **39%** | 79% | 0.32 |

Aggregating an evaluation over the exact information set (mean or worst case) is the best
single-move predictor, but only by 5 points over the true board at depth 6 and on 354
decisions; this is suggestive, not proof. If Greek Gift sampled one board and played its
top-1, the expected agreement with "plurality" would be the mean P column (0.32), which is
what we see for plurality (36%), so sampling is not excluded by this table alone; it is
excluded by Test 4 (the zero-information states) and by Test 1 (randomness with one board).

## Test 3: material and tactics (true board, depth 10)

* 846 of 3,987 scored decisions (21%) are captures. The capture is Stockfish's top move
  68% of the time and in its top 3 90% of the time.
* Stockfish's top move is a capture but Greek Gift played something else in 402 decisions
  (10%). The victim is always visible (by the rules an attacked piece is visible). Victim:
  pawn 291 (72%), knight 58, bishop 29, rook 20, queen 3, ep 1. The target is undefended on
  the true board in 231 (57%) and defended only by pieces Greek Gift cannot see in 143 (36%);
  defended by a visible piece in only 27 (7%). On its last-seen board the target has no
  defender in 220 of the 402. Median cp gap of the declined capture 52 (mean 166). So the
  pattern is: it declines pawn (and some piece) grabs whose safety it cannot verify, even
  when the true board says they are free, and it almost never declines a capture that is
  refuted by something it can see. Its own captures that Stockfish does not rank first are
  mostly pawn captures with a gap under 50 cp (87 of 270).

## Hypothesis

Greek Gift is **not** "Stockfish with a sampling temperature on a sampled board". The
evidence against: (1) in fully-known positions its agreement with Stockfish is flat at
55-63% from depth 4 to 15 and 0.5 to 5 s, far below the ~100% a Stockfish user would show at
its own depth; (2) its opening repertoire ignores Stockfish's evaluations (1.d4 90/90 with e4
preferred at every depth; Nf3 0/44 while Bf4 21/44; as Black never e5 although it is top-1
on 55% of the possible boards), which no temperature reproduces; (3) it is non-deterministic
in positions with a single consistent board, so the randomness is not belief sampling;
(4) its choices track the true board twice as well as a last-seen memory and best of all the
mean evaluation over the exact set of consistent boards.

What fits: a weighted opening book (1.d4; c4/Bf4 50/50 after ...d5; as Black c6 53%, Nf6 36%,
a few rare lines), then an engine-strength evaluator (its deviations from Stockfish cost a
median 15-25 cp; top-3 80%) applied to an explicit belief that is close to the exact
information set, aggregated by expectation (mean over boards) with a risk penalty on captures
whose defenders could be hidden, and a timed search (about 6 s per move early, 5.3 s by ply
55) that supplies the residual ~10% non-determinism. Whether the evaluator is Stockfish
behind this aggregation or another engine cannot be decided from these data; the aggregation
layer, not the engine, is what separates it from a plain Stockfish bot.

Falsifiers: (a) score the information-set members at depth 10+ on 1,000+ decisions: if the
best-mean move does not beat the true-board top-1 by a clear margin (here 39% vs 34% at depth
6, n = 354), drop the expectimax claim; (b) find a known-board position where it deviates
from Stockfish's top-1 by > 100 cp *repeatedly* across games (Bb5 at ply 19 is one instance in
two games) and check whether another engine ranks that move first; if Stockfish at any depth
ranks it first on the mean over its belief, the deviation is belief, not evaluator;
(c) if more identical fully-known positions across games show divergent choices with large
evaluation gaps, the noise is a sampling temperature on the move list after all, and the T
should be fitted on those non-book positions, not the opening; (d) a run of Black first moves
that includes e5 or d5 at ~50% would reinstate board sampling at move 1.
