# Obscuro v1

A reduced version of Obscuro ([Zhang and Sandholm, arXiv:2506.01242](https://arxiv.org/abs/2506.01242)).
The bot is `bots/obscuro/`; the algorithm is the `fow/obscuro/` package. The team doc
"Obscuro: the search pipeline, formally" has the full derivation.

## One move

1. **Belief** (`belief.py`). Keep P, every position consistent with our observations,
   filtered exactly after each ply and capped at 1,500 states.
2. **Subgame** (`subgame.py`). Sample up to 200 roots from P and build a depth-2 game:
   chance picks a root, we move (one infoset, since every root looks the same to us),
   the opponent replies (infosets keyed by what it sees), leaves are scored by the heuristic.
3. **Solve** (`regret.py`, `solver.py`). Alternating PCFR+ on that game.
4. **Move** (`search.py`). Play the top action of the last iterate.

## Differences from the paper

| | Paper | v1 |
| --- | --- | --- |
| Belief | Exact P, up to 10^6 states | Capped at 1,500 by uniform subsampling |
| Roots | KLUSS: our infoset plus histories the opponent confuses with it | Uniform sample of P each turn |
| Opponent infosets | Full observation history | Current observation and legal replies |
| Subgame safety | Resolve / Maxmargin gadget, tree reused across turns | None; tree rebuilt every turn |
| Tree | Grown by one-sided GT-CFR | Fixed depth 2 |
| Leaf eval | Stockfish 14 | Material + squares occupied or attacked |
| Move choice | Up to 3 stable moves when safe | Top action only |

What these cost: no bluffs that rely on the opponent fearing positions we know are false;
the opponent is modeled as forgetting its past observations; roots are weighted uniformly
instead of by the opponent's likely play; and the search sees only one reply deep.

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
  The bot logs a repair count.
- **Time.** `min(remaining / 30 + 0.8 * increment, remaining / 5)` seconds per move. The belief
  update runs in `observe()`, on our clock, so the bot times it and subtracts it from the
  budget; each move's log line reports it as `belief_update`.
- **Errors do not end the game.** An exception leaving `observe()` or `act()` exits the
  process, which the referee scores as a loss. The bot catches them and degrades in steps:
  if the belief update fails, the old states are projected onto the current observation
  (counted as a repair); if the search fails, has no usable belief, or has under 0.1 s, the
  bot plays a fallback move from the tracker's legal list (best capture that does not leave
  our king attacked by a visible piece). Tracebacks go to stderr.

- **Repetition avoidance.** The search has no memory, so when winning it can shuffle the
  same moves until the game is drawn by threefold repetition. The bot counts the
  (observation, move) pairs it has played. When the search value is above 0.1 and the top
  move repeats one of them, each earlier play costs that move 0.05 and the best move after
  the discount is played (`choose_action` in `search.py`, logged as `repeat_avoided`).
  Nothing changes when we are not ahead or the top move is new.

Not modeled: the 100-ply and 1,000-ply draws, repetition inside the search tree, and exact
visibility in the heuristic.

## Next

In the order the paper's ablations suggest:

1. **GT-CFR expansion** instead of the fixed depth-2 tree (needs a general tree in place of
   the flat arrays; `regret.py` carries over unchanged).
2. **Purification over up to 3 stable moves**, so the bot mixes when it is safe to.
3. **Tree reuse with the Resolve / Maxmargin gadget**, which also gives real root weights.
4. **KLUSS roots**: add the histories the opponent cannot tell apart from ours.
