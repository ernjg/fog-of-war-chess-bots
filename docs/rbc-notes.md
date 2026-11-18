# RBC / FoW winners vs v4 — research notes (2026-11-17)

Sources (primary): SF1 code https://github.com/ginop/reconchess-strangefish (config.yml, strategies/multiprocessing_strategies.py); SF2 code https://github.com/ginoperrotta/reconchess-strangefish2 (strangefish/strangefish_strategy.py, utilities/rbc_move_score.py); Fianchetto thesis https://taufeeque9.github.io/assets/pdf/bachelors_thesis.pdf; 2019 report http://proceedings.mlr.press/v123/gardner20a/gardner20a.pdf; 2021 report https://proceedings.mlr.press/v176/perrotta22a/perrotta22a.pdf; 2022 report https://proceedings.mlr.press/v220/gardner23a/gardner23a.pdf; Penumbra https://arxiv.org/abs/2110.01810; ZS21 dark chess https://arxiv.org/abs/2106.06068; Obscuro https://arxiv.org/abs/2506.01242; Scorca/ToM https://www.scitepress.org/Papers/2024/123542/123542.pdf. Kevin and Dyn-Dog: no code or write-up found beyond the tournament reports.

## 1. Board weighting (opponent model)
- **StrangeFish/SF2 (won 2019, 2022):** no move model. Weight = sigmoid of Stockfish depth-7 eval of the board *from the opponent's point of view*: `w = 1/(1+exp(-2·ln3·s/3000)) + 0.02` (s in cp; 0.9 at +3000; opponent-in-check boards scored −4000 → w≈0.07). Not normalised over the opponent's moves from a parent; Fianchetto §3.2 criticises exactly this.
- **Fianchetto (won 2021, 91%):** persistent Bayes belief `P(s'|b,z) ∝ P(z|s',a)·P(s'|s,a)·P(s|b)` with `P(a|s)` = Lc0 policy (T75 net); then mixed with uniform, `λ = 0.8 if |I|<5000, 0.5 if 5000–20000, 0 if >20000` (pass gets uniform). 2022 version added "increased weight to defensive sensing and moving to detect opponent attacking moves that have been given a low probability", opponent-specific (2022 report, Table 1).
- **Kevin (3rd/4th):** 2021: depth-limited unsafe CFR over sampled boards to get the opponent's distribution; 2022: ResNet+LSTM imitation of SF2 logs predicting opponent moves and senses; move = argmax expected win probability.
- **Obscuro / ZS21:** no opponent model; sample ≤ "a few hundred" positions uniformly from P (|P|≤1e6; ZS21 L=200). Newly sampled roots assume the *opponent knows the exact position*, alternate value `min(ṽ(h), v*)`. Resolve root distribution `α(J)=½(y(J)/Σy + 1/m)`.
- *Applies to us:* our 1-ply Stockfish softmax is closer to Fianchetto than to SF2. Fianchetto's two corrections are the ones we lack: a set-size-dependent uniform mixture and a deliberate boost of low-probability king-attacking moves.

## 2. Scoring across boards
- **SF1 2019:** `0.9·weighted mean + 0.1·unweighted min`. **SF2 2022:** `0.7·weighted mean + 0.3·unweighted min`, then random choice among moves within 10 cp of the best. Min is over *all evaluated boards regardless of weight*; with `into_check_score=−7000` (+`−2000` if already in check) any move capturable on any sampled board loses ≥2100 cp of compound score — effectively a veto. Last 60 s: mean 1.0, min 0.
- **Penumbra:** paranoia `argmax (1−ϕ)·q/n + ϕ·m + c·π·√(ln n/n)`, m = min seen; grid best at ϕ=10%, caution 20% (1726 Elo), ϕ=30% worst (1666–1691), CI ±19.
- **Others:** wbernar5 pure worst-case Stockfish → 5th 2019; Oracle unweighted majority → 3rd 2019 / 5th 2021 / 6th 2022; ROOKie 2022 (5th): equal votes for top-5 moves per board, votes *against* any move leaving the king in check; JKU-CODA: "combination of worst-case and weighted-average".
- **ZS21/Obscuro:** value `tanh(cp/600)` (6 pawns) from Stockfish depth 1 (Obscuro: SF14 MultiPV depth 1 per expanded node); CFR, not averaging.
- *Applies to us:* v4's `-risk+(1-risk)·mean` with weighted risk has no unweighted worst-case term. SF2's evidence (won 2022 with 0.3·min) and Penumbra's grid both say a *small* unweighted min term helps and a large one hurts.

## 3. King-capture risk
- SF2 `rbc_move_score.py`: `capture_king_score=+9000+material`, `into_check_score=−7000`, `remain_in_check_penalty=−2000`, and `count_weak_squares`: −1 cp per empty square on our king's rank/file (if opponent has Q/R), diagonal (Q/B), knight squares (N) — an explicit open-line penalty; mirrored as a bonus against the enemy king.
- Fianchetto "faraway defense": when likely in check, incentivise blocking with a supported piece instead of moving the king (opponent likely senses king and attacks, loses the attacker). Sneak-attack reward made piece- and risk-dependent (SF: constant).
- Obscuro appendix E: the a4–e8 diagonal; all 10 games ≤12 ply in 10,000 self-play games ended with an uncovered Qa4+/Qa5+; Black almost never plays d5 and closes the diagonal with c6; White prefers d4/c4 (66%/30%) over e4 (2%).
- *Applies to us:* open-line penalty is cheap and targets precisely our loss pattern; opening book closing long lines is free.

## 4. Time
- SF2: `turn = clamp(remaining/16, 3 s, 40 s)`, 70% sense / 30% move; UCT-style sampling of (move, board) pairs (`exploration 1000·√ln N`), stop when the top move is stable 100 iterations; boards scored during the opponent's turn; opponent-specific parameter overrides by name.
- Obscuro: time ∝ remaining; each doubling of time/move ≈ 52–57% vs half (10k games each); depth 10.7 plies at 5 s/move.
- *Applies to us:* at 180+2 s, spend search on contending moves only (UCT over moves), not all candidates × 64 boards.

## 5. Information / trap heuristics
- SF2: `capture_penalty=−5` (reveals position), `passing_reward=+5`, `reward_attacker=+20` only if non-capture ("sneak"), `unsafe_attacker_penalty=−15` if an evasion captures, `reward_check_threats=+15` per quiet check available, hanging material 0.1×, pawn pressure +15/+5, `use_absolute_score=0.85`.
- ZS21: entropy penalty `2^−H(a)·|I|/M`, M=1e7, only to keep the set small.
- Obscuro: purification (mix among ≤3 top actions only when the strategy is safe) was its largest ablation: 70.2% vs no purification. Partly applicable (FoW shows the capture square to the victim's attackers only; uncertain).

## 6. Evidence on weighting vs scoring (Q3)
- Fianchetto Table 1 (60-game matches): V1 (Lc0, SF weights) → V2 (Bayes belief): 24–36 → 39–21 vs StrangeFish, 13–47 → 35–25 vs SF2, 36–24 → 46–14 vs Oracle. Fig. 4: probability on the true board consistently higher than StrangeFish's. V3 heuristics: 39–21 → 48–12 vs StrangeFish but "no clear gains" on the server.
- Scoring-rule evidence is weaker: Penumbra's paranoia grid is within ±19 Elo except ϕ≥20%; SF changed 0.9/0.1 → 0.7/0.3 between wins with no published ablation.
- Scorca ToM (opponent-knowledge replay): 60% → 70% vs Trout over 10 games (not significant).
- 2021 report: "Top performing bots tend to predict their opponent's moves"; Stockfish top-3 agreement does not rank bots (Oracle 73% but 5th; SF2 59%/62% and 1st in 2022).

## Caveats
RBC has sensing and 15 min/game, no increment; parameter values are RBC-tuned. Kevin's internals are known only from one paragraph per report. Fianchetto's 2022 "defensive weights" have no published numbers. Obscuro's code is not public.
