# Obscuro

A reduced version of Obscuro ([Zhang and Sandholm, arXiv:2506.01242](https://arxiv.org/abs/2506.01242)).
The bot is `bots/obscuro/`; the algorithm is the `fow/obscuro/` package. The team doc
"Obscuro: the search pipeline, formally" has the full derivation.

The bot keeps a belief set and has two ways to pick a move from it. With a Stockfish binary
it uses the [Stockfish search](#stockfish-search); without one, or whenever that search
cannot answer, it uses the PCFR+ search described first. Its first stderr lines say which.

## One move (PCFR+ search)

1. **Belief** (`positions.cpp`, `position_set.py`; `belief.py`). Keep P, every position
   consistent with our observations, filtered exactly after each ply. A compiled helper
   keeps it in full, up to 200,000 states (see [The position set](#the-position-set));
   without the helper Python keeps it, capped at 1,500. With Stockfish running, each
   state also has a weight: how likely the opponent's unseen moves that lead to it are
   (see [Weighted belief](#weighted-belief)).
2. **Subgame** (`subgame.py`). Sample up to 200 roots from P and build a depth-2 game:
   chance picks a root, we move (one infoset, since every root looks the same to us),
   the opponent replies (infosets keyed by what it sees), leaves are scored by the heuristic.
3. **Solve** (`regret.py`, `solver.py`). Alternating PCFR+ on that game.
4. **Move** (`search.py`). Play the top action of the last iterate.

## Stockfish search

Step 1 is the same. Steps 2 to 4 are replaced (`stockfish_search.py`, `engine.py`):

2. **Scan.** Draw 256 states from P in proportion to their weights; a state drawn several
   times is looked at once and counts that many times. (Without weights: every state once,
   in random order, up to 256.) On each, split our moves into orthodox-legal moves, moves
   that leave our king capturable there (an immediate loss), and castling out of or through
   attack (legal only in Fog of War).
3. **Score.** Two Stockfish processes search up to 64 of those states, the ones drawn most
   often first, with MultiPV, which
   gives every orthodox-legal move a value on each state: `tanh(centipawns / 600)`, the
   paper's scale, plus a small term that keeps rising so that the larger of two winning
   scores still counts for more. They share the move's time equally and report the deepest
   iteration they finished, typically depth 5 to 8. A Fog-of-War-only castling move is
   scored from the position after it.
4. **Move.** For each move, `value = -risk + (1 - risk) * mean`, where `risk` is the share
   of scanned states in which it loses the king and `mean` is its average Stockfish value
   over the states where it does not. In both, a state in which our king is attacked counts
   six times (see below). Play the best, with the same repetition rule as below.

Why this is a fair swap: in the depth-2 game two belief states never look alike to the
opponent, because it always sees its own pieces. So the PCFR+ search already treats the
opponent as knowing the position, and Stockfish does the same, only deeper and with a real
evaluation. What neither search has is the paper's reasoning about what the opponent does
not know about *our* pieces (KLUSS roots).

Why attacked states count six times: an opponent who can attack our king out of sight
usually does, more often than P allows for. Replaying 28 games (1,053
decisions) against the true boards, the plain share underestimated the chance of losing the
king two to four times over; when 1 to 5% of the states had our king attacked, it really was
attacked 15 to 25% of the time. A weight of 6 on those states makes the predicted number of
lost kings match the actual number. When no state has the king attacked, it never was: none
of the 31,389 moves given zero risk lost the king. On 34 later games (1,965 decisions) that
had no part in choosing it, a weight near 4.5 matches the count, and between 1 and 12 the
quality of the chosen moves changes by a few percent at most, so the 6 was kept. (Those
replays were made without weights. With a weighted belief the share is closer to the
truth and a factor of 2 would match the count; the 6 stays, for the reason given at the
end of [Weighted belief](#weighted-belief).)

What Stockfish is not trusted with:

- **Positions it cannot take.** Stockfish 19 exits on a position it considers impossible,
  for example one where the side to move can capture the king. `engine_accepts` mirrors its
  checks and such states are skipped. Positions reached by play always pass, and a belief
  repair keeps the opponent's material possible, so that its states pass as well. A test
  sends several hundred of each kind to the real engine.
- **Fog of War rules.** King safety is decided by our own code, not by the engine. A move
  after which the opponent has no safe reply is a win. Stockfish calls that a draw when it
  is stalemate (here the stalemated side must move and lose its king), so every move it
  scores as exactly 0 is checked. A move it calls mate in one is checked too: here the king
  may castle out of check, and where that saves it the move is worth, on that state, no
  more than the worst of the other moves. At 99 plies
  without a capture or pawn move, any other move is scored as the draw the referee declares
  before the opponent has to answer. A state whose count is 100 or more cannot have the
  real one (the opponent moved a pawn out of our sight at some point); it is sent with a
  count too low to matter.
- **Staying alive.** Every wait on an engine has a deadline. An engine that exits or stops
  answering is killed, its states are left out of the average, and the log says why; output
  that is not a search line is ignored. Dead engines are replaced up to three times per
  game. That runs on our clock, so it is only tried when half of what the move has left
  (3 s at most) is at least one and a half times what an engine needed to start. Engines
  that did not come up before the game are tried again on the first moves in the same
  way. If no state gets scored, the PCFR+ search runs with what is left of the move's
  time; if that is under 0.1 s the fallback move is played. The log says which.
- **Reports after "stop".** A search stopped mid-iteration prints a last report that mixes
  depths and can contain placeholder scores. Only completed iterations are used.

### Weighted belief

P says which positions are possible, not which are likely. Counting them all alike amounts
to assuming that the opponent plays its unseen moves at random. In one arena game the bot
recaptured on d4 with a knight and lost it to the queen: the opponent had retreated the
queen to d8 and brought a knight to c6, two natural moves, but in P each was one move
among thirty.

So each state has a weight (`belief.py`, `opponent.py`):

- **Where it comes from.** After each opponent move, Stockfish scores every move the
  opponent had, one ply deep, in each state that was possible before it. A softmax turns
  the scores into odds (temperature 0.06 on the value scale, about a third of a pawn),
  mixed 80/20 with equal odds so that no move is ruled out. A state's weight is its
  parent's weight times the odds of the move, added up over all the ways to reach it; a
  test compares the result with a count over every sequence of unseen moves. A state in
  which the opponent could have taken our king, and did not, keeps 2% of its weight.
- **What it models.** Good play, not any particular opponent, and it judges the moves as
  if the opponent saw the whole board. Obscuro gets its weights from the opponent strategy
  that its previous search computed, mixed half and half with equal odds; this is the
  same idea without the search tree.
- **Where it is used.** The search draws its states by weight (above). When the set has to
  be cut to the cap, the heaviest three quarters of the cap are kept and the rest is drawn
  at random from the other states, each drawn state's weight scaled up to stand for the
  ones not drawn, so that unlikely states keep their share. States a top-up adds
  (`replenish`) are grown from likely states and get a quarter of the weight between them.
- **What it costs.** A third of a millisecond per state on the development machine, and
  per move at most 0.5 s and 15% of the move's time; states the engines did not get to (the
  lightest) use equal odds. It is timed as part of the belief update, so the cap that
  follows the clock makes room for it.

Measured by replaying our side of 100 public arena games (2,675 decisions) against the
true boards, with a Python belief capped at 800 states, without weights and with them.
Each decision is searched for half a second from both beliefs; the engines' memory is
cleared before every search and the order alternates, so that neither profits from what
the other has just searched. (An earlier comparison did not do that and flattered whichever
was searched second.)

| | Without weights | With weights |
| --- | --- | --- |
| True position is in the belief | 42% | 63% |
| Probability the belief gives it (mean) | 2.7% | 6.0% |
| Value lost by the chosen move (mean, true board, Stockfish depth 10) | 0.048 | 0.041 |
| ... against teams rated 1600 and up (46 games) | 0.050 | 0.040 |
| ... against the others (54 games) | 0.045 | 0.043 |
| Chosen moves that lose more than 0.3 | 83 | 62 |
| Chosen moves that lose the king | 50 | 47 |

The difference in the third row is two and a half standard errors, counting each game as
one observation; the total was better in 62 games and worse in 34 (against the stronger
teams, 37 and 9). Against the weaker teams there is no difference to speak of, in either
direction. Mixing the weights half and half with equal odds in the search, or flattening
them, was no better.

What the weights do not fix: they judge the opponent's moves as ordinary chess would. A
check from a square we cannot see is a poor move there if it can be blocked, so it gets a
low weight; here it is a strong move, because we may not answer it. That is why the
number of kings lost hardly changes, and why states with our king attacked still count
six times: with a factor of 2 the weighted search twice lost its king, in eight local
games as White against the previous version, to a queen check on the e-file that the
weights put at 2%. Obscuro has no such rule and needs none: its search over the whole
set of positions finds for itself that a hidden check is strong (see [Next](#next)).

In a move line, `ess=57` after `|P|=...` is the effective number of states: the size of
the set when all weigh the same, about 1 when one state has nearly all the weight. At the
end, `policy=412/650` says that Stockfish was asked about 650 states after the opponent's
last move and answered for 412 in the time it had; the others used equal odds.
`--equal-odds` switches the weights off. The temperature, the mix and the time limits are
at the top of `opponent.py`; the shares used when cutting and topping up at the top of
`belief.py`.

### The position set

Obscuro keeps every position consistent with what it has seen. In Python the update costs
about a millisecond a position here and four to five times that in the arena, so
`belief.Belief` holds a few hundred and has to sample, and the true position is then often
not among them. `positions.cpp` is the same update in C++, a few microseconds a position:
25,000 positions in 60 ms here. It runs as a helper process, like the engines, and keeps
the set up to 200,000 states; a larger one is cut down as before (the likeliest states
first).

- **The rules are the referee's.** The helper generates python-chess's pseudo-legal moves,
  castles without any attack test, and sees for a side its own squares and every square
  one of its pieces could move to. The tests compare it with the referee on 2,000 positions
  (the moves in order, what each side sees, the position after every move; 5.5 million such
  checks were run once, without a difference) and with `Belief` on whole games: after
  every ply the two hold the same positions with the same weights. `positions selftest`
  repeats a small part wherever it is built, and `build.sh` keeps the binary only if that
  passes.
- **What Python sees.** `position_set.PositionSet` has `Belief`'s interface. Its `states`
  are the whole set while it has at most 256 states, and otherwise 256 draws by weight
  (each state once, with its number of draws as its weight): what the search would have
  drawn itself. `len()` is the size of the full set, and that is the `|P|` in the log.
- **The policy** is asked about the 512 heaviest states (it costs Python a quarter of a
  millisecond a state); the others get equal odds, as they did when its time ran out.
- **What `Belief` still does**, on what Python has of the set: rebuilding a set that an
  observation has emptied and topping up a thin one. Both can only happen after the cap
  has cut the set, which is rare now.
- **If the helper is lost** (no answer in time, or it exits), the game goes on with a
  `Belief` started from what Python last saw, and the log says so once. If it was never
  built, or does not start, the bot says so and uses `Belief` from the first move.

The same replay as above, with a third belief: the full set, weighted by the same policy.

| | No weights, Python | Weights, Python (800) | Weights, full set |
| --- | --- | --- | --- |
| True position is in the set | 42% | 63% | 93% |
| Probability the set gives it (mean) | 2.7% | 6.0% | 8.3% |
| Value lost by the chosen move (mean) | 0.048 | 0.041 | 0.038 |
| Chosen moves that lose more than 0.3 | 83 | 62 | 51 |
| Chosen moves that lose the king | 50 | 47 | 46 |
| Time to update, per move, on this machine | 0.30 s | 0.39 s | 0.21 s |

Against the capped belief with weights the full set's gain in value is two standard errors
(better in 51 games, worse in 41); against no weights, nearly five. It does not lose fewer
kings. Half of those are lost in the 15% of decisions where even 200,000 states are not
the whole set, and in the others the true position is there but its weight is small: the
weights still judge a hidden attack as ordinary chess would. That is the search's part
(see [Next](#next)). The update is also the cheapest of the three, and in the arena, where
Python is slower and C++ is not, by a much wider margin.

### Setting it up

The Stockfish source is not in the repository. Fetch it once (about 100 MB, gitignored):

```sh
bash bots/obscuro/fetch_stockfish.sh     # Stockfish 19 and its network, checksum verified
```

Locally, build a copy for your machine anywhere outside `bots/` and point the bot at it
with a full path (`run.sh` changes directory, so a relative one is not found):

```sh
rm -rf /tmp/sf && cp -R bots/obscuro/stockfish /tmp/sf
make -C /tmp/sf/src -j build ARCH=apple-silicon COMP=clang \
    EXTRACXXFLAGS=-DNNUE_EMBEDDING_OFF                 # Linux: ARCH=x86-64-avx2 COMP=gcc
export FOW_STOCKFISH=/tmp/sf/src/stockfish             # 'off' plays without Stockfish
uv run pytest -rs                                      # -rs lists what was skipped, and why
```

On a Mac whose linker cannot find the SDK (`ld: ... tapi` errors), run
`export SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk` first; the same goes
for rehearsing `build.sh`. Without `FOW_STOCKFISH` the tests that need the real engine are
skipped.

The position-set helper is one file with nothing to fetch. The tests build it themselves
(and are skipped where there is no C++ compiler). To play with it locally:

```sh
c++ -O2 -std=c++17 -o /tmp/positions bots/obscuro/positions.cpp
export FOW_POSITIONS=/tmp/positions                    # 'off' keeps the set in Python
```

For local games between two bots that both use Stockfish, give each bot its own folder
with a copy of the binary and of `nn-*.nnue` beside it (a hard link to the network file is
enough), and point each bot at its own with `--stockfish` in a small `run.sh` of its own;
`FOW_STOCKFISH` is one variable and would give both the same file. Engines started from
the same binary file share the network in memory, and a paused bot's engines then hold up
the other bot's engine start by about a second each, which can leave it with fewer.

In the arena, `bots/obscuro/build.sh` compiles the source that travels in the ZIP
(`uv run tools/package.py obscuro` copies the whole bot folder, about 80 MB zipped). It
logs the sandbox's CPU flags, compiles with plain `g++`, three files at a time, and then
starts the binary through the bot's own engine code and has it score the starting position
(a check that fails is repeated once). A binary that exits there (as one would on a CPU
without AVX2) or a build that does not compile is reported as not built. No step runs past
the 5-minute limit.

Before Stockfish, `build.sh` compiles `positions.cpp` (a few seconds) and runs its
self-test; the binary is kept only if that passes.

The script exits 0 whatever happens, because without Stockfish the bot still plays, on the
PCFR+ search, and without the helper it keeps its set in Python. A version like that would
be accepted, and its results would say nothing about either. To have it rejected instead,
create empty files `bots/obscuro/REQUIRE_STOCKFISH` and `bots/obscuro/REQUIRE_POSITIONS`
before packaging: the build then fails unless both engines start and search, and unless
the helper was built, and its log says near the top which of the files are present. Or
upload with "Activate automatically" unchecked and activate after reading the log.

After an upload, check three things:

- The build log has a line `build: POSITION SET OK: g++, ...s; selftest ok: ...`
  (`build: POSITION SET NOT BUILT: ...` gives the reason), and a game's stderr begins with
  `obscuro: position-set helper ready in ...s`.
- The build log ends with `build: STOCKFISH OK: ...; 2 of 2 engines ready in ...s, 20 of 20
  opening moves scored to depth ...`. `build: STOCKFISH NOT BUILT: ...` gives the reason.
- In a game's private stderr the move lines read `obscuro: sf ... eng=2 ...`. Lines without
  `sf` are PCFR+ moves, and `eng=1` means an engine was lost. The second line of the log is
  `obscuro: stockfish ready: 2 of 2 engines in ...s, binary <path>`, but the arena keeps
  only the last 16 KiB (a little over 100 of our moves), so in a long game go by the move
  lines.

In a move line, `|P|=1500~` is the size of the belief (`~`: it is a sample), and
`|P|=600~/600` means the clock has lowered the cap to 600 (see Time below).
`belief_update` is what updating it cost this turn.

To rehearse the build, package the bot, unzip `dist/obscuro.zip` somewhere outside the
repository and run `bash build.sh` there, then a game with that folder's `run.sh` and with
`FOW_STOCKFISH` unset (`env -u FOW_STOCKFISH ...`), so that the game uses the binary just
built: the ready line names it. On a Mac the script compiles with clang instead; the g++
recipe runs only on Linux (the tests run that branch with stand-ins for the tools, which
shows the script's logic but not whether g++ accepts the flags).

`MAX_ROOTS`, `SCAN_STATES`, `MAX_DEPTH` and the time slices are at the top of
`stockfish_search.py`; `--engines` sets the number of Stockfish processes (default 2, one
per physical core in the arena).

## Differences from the paper

| | Paper | This bot |
| --- | --- | --- |
| Belief | Exact P, up to 10^6 states | Exact up to 200,000 states (compiled helper; fewer when the clock is short), then the likeliest states first; once sampled, topped up towards 128 states where the fog allows. Without the helper, capped at 1,500 |
| Root weights | From the opponent strategy of the previous search, mixed half and half with equal odds | From Stockfish's one-ply scores of the opponent's moves, mixed 80/20 with equal odds (PCFR+ search: none) |
| Roots | KLUSS: our infoset plus histories the opponent confuses with it | Drawn from P each turn, by weight. Stockfish search: states with our king attacked count six times |
| Opponent infosets | Full observation history | PCFR+ search: current observation and legal replies. Stockfish search: the opponent knows the position |
| Subgame safety | Resolve / Maxmargin gadget, tree reused across turns | None; tree rebuilt every turn |
| Tree | Grown by one-sided GT-CFR | PCFR+ search: fixed depth 2. Stockfish search: alpha-beta on each root, to depth 12 at most |
| Leaf eval | Stockfish 14, depth 1, inside the tree | PCFR+ search: material + squares occupied or attacked. Stockfish search: Stockfish 19 searches each root itself |
| Move choice | Up to 3 stable moves when safe | Top action only |

What these cost: no bluffs that rely on the opponent fearing positions we know are false;
roots are weighted by a one-ply judgement of the opponent's moves rather than by a
strategy the search worked out; in the PCFR+ search the opponent is modeled as forgetting
its past observations and the search sees only one reply deep; in the Stockfish search the
opponent is modeled as knowing the position.

## Data layout

The subgame (`subgame.py`) is four plies of structure stored as flat NumPy arrays:

    chance picks a root r            (uniform over the sampled roots)
    we pick a move a                 (one infoset: every root looks the same to us)
    the opponent picks a reply b     (infoset keyed by its observation and legal moves)
    leaf value                       (terminal result, else the heuristic)

Opponent nodes are indexed `j = r * n_actions + a`. Each opponent infoset owns a
contiguous block of "slots", one per legal reply, so `slot_infoset[s]` names the infoset
of slot `s` and `infoset_start` marks each block. A leaf is the pair (node `j`, slot).
`regret.py` runs regret matching over these slots with counterfactual values to maximize;
the solver negates them for the opponent, who minimizes our value.

The heuristic (`evaluation.py`) approximates a side's visible squares by the squares it
occupies or attacks. That is cheaper than the referee's exact visibility and misses pawn
pushes and en passant.

## Design choices

- **Flat arrays, not a tree walk.** The depth-2 game is stored as NumPy arrays and one PCFR+
  iteration is two `bincount` passes over the leaves, so a move gets thousands of iterations
  in Python. The Nash gap is about 0 every move.
- **Most of the budget builds roots.** Building one root costs 20 to 30 ms while the solve
  converges in a few hundred iterations, so 80% of the move time goes to sampling roots.
- **Legal replies in the infoset key.** Guarantees every node of an opponent infoset has the
  same actions, without relying on the observation to determine them.
- **Belief repair.** If the cap drops the true position and an observation leaves no
  survivor, the previous states are projected onto the observation instead of emptying P.
  A piece that has just come into view was guessed somewhere out of sight a move before,
  so the projection would count it twice: as many unseen pieces of that kind are taken
  out again (with two queens and eight pawns, Stockfish would refuse every state). The
  projection is then corrected by the two things the fog tells us through our pawns
  (`fit_to_view`): an unseen square straight ahead of a pawn of ours holds an opponent
  piece, and an unseen square it attacks holds none. The bot logs a repair count. A
  rebuilt set does not know about a possible en passant capture; if the tracker offers one
  that no state allows, the bot searches the other moves.
- **A sampled belief is kept wide.** P is exact until the cap or a repair drops states
  (`Belief.exact`). After that the true position is usually gone, and each revealing
  observation kills most of what is left. In one test game the set went from 1,500 states
  to 2 with 23 squares still unseen, and the Stockfish search, taking those 2 states as
  the truth, gave away a queen for a mate that was not there while 11 points ahead. So
  whenever a sampled set falls under 128 states it is topped up (`Belief.replenish`) with
  states that differ from existing ones by one to eight opponent moves made out of our
  sight (mostly one to three, castling included), each checked to produce exactly the
  current observation. After a repair, states that do not produce it are dropped as soon
  as one that does exists. An exact set is never touched: there, few states means we
  really know. In the log, `|P|=128~` marks a sample.
- **Time.** `min(remaining / 30 + 0.8 * increment, remaining / 5)` seconds per move. The belief
  update runs in `observe()`, on our clock, so the bot times it and subtracts it from the
  budget; each move's log line reports it as `belief_update`. If that leaves under 0.4 s
  while 20 s or more is on the clock, the move still gets 0.4 s of search: a slow belief
  update should not cost a whole move.
- **The belief follows the clock.** The update tries every move of every state, so its
  cost grows with the number of states, and nothing else in a move is as expensive: on
  the development machine a full set of 1,500 takes about a second, and up to three. On a
  slower machine that alone would exceed what a move may spend, leave nothing for the
  search and run the clock down. So the bot measures what an update costs per state and
  keeps the cap at what 40% of the move's time pays for (never under 128): a larger set
  is cut down (at random, or with weights the likeliest states first), and the cap goes
  back up when the clock allows.
  With plenty of time on a fast machine nothing changes.
- **Errors do not end the game.** An exception leaving `observe()` or `act()` exits the
  process, which the referee scores as a loss. The bot catches them and degrades in steps:
  if the belief update fails, the old states are projected onto the current observation
  (counted as a repair); if the search fails, has no usable belief, or has under 0.1 s (on
  a low clock, see Time), the bot plays a fallback move from the tracker's legal list (best
  capture that does not leave our king attacked by a visible piece). Tracebacks go to stderr.

- **Repetition avoidance.** The search has no memory, so when winning it can shuffle
  until the game is drawn by threefold repetition. A position can only repeat if our own
  pieces stand where they stood before, and those we always know, so the bot counts how
  often they have stood in each arrangement (at the start and after each move of ours).
  When the search value is above 0.1 and the top move goes back to an arrangement, the
  first time back costs it 0.05; a second time back may be the third occurrence, which is
  a draw, and costs half of what we are ahead by. The best move after the discount is
  played (`own_placement` and `choose_action` in `search.py`, logged as
  `repeat_avoided`). Nothing changes when we are not ahead. An earlier version counted
  the (observation, move) pairs it had played and missed repetitions reached by different
  moves: in one arena game a rook came to d5 three times from three squares and the game
  was drawn 13 points ahead.

Not modeled: the 100-ply and 1,000-ply draws, repetition inside the search tree, and exact
visibility in the heuristic. (The Stockfish search does see the 100-ply draw coming: each
state's count is passed to the engine.)

## Next

The paper's own steps, one at a time, in the order its ablations suggest. The Stockfish
search averages over positions searched separately, which is not what Obscuro does; the
PCFR+ search is the part with Obscuro's shape, and these build on it:

1. **Stockfish values at the leaves** of the PCFR+ tree in place of the material heuristic
   (the paper's largest single gain), with the belief's weights as the chance node's odds.
2. **GT-CFR expansion** instead of the fixed depth-2 tree (needs a general tree in place of
   the flat arrays; `regret.py` carries over unchanged).
3. **Purification over up to 3 stable moves**, so the bot mixes when it is safe to.
4. **Tree reuse with the Resolve / Maxmargin gadget**, which gives the paper's root weights.
5. **KLUSS roots**: add the histories the opponent cannot tell apart from ours.
