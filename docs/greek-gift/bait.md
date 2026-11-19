# Does Greek Gift model its opponents' blindness?

**Short answer: no evidence of it. Its "Greek gifts" are Stockfish moves on the true board: in 37 of 39 bait wins the bait is Stockfish's top move at depth 12 or within 30 cp of it (31/39 are scored as forced mate on the true board), and 38/39 are within 80 cp. Over 60 sampled games its moves match a full-information engine as closely as ours do, and where it deviates from the engine it gains no measurable blindness advantage (no fewer pieces seen by the enemy, no more attacks from unseen squares, no more unseen king threats). Stockfish's own top move would attack from the fog *more* often than Greek Gift does. A full-information engine on a good belief reproduces its play; the thing that makes the bait work is the opponent's side of the board, not a model of it.**

Data: all 179 arena games of Greek Gift (f394d843..., v30) and our 150 arena games (Magnus Monte Carlsen v4). Replays via `starter/referee.py` `FowBoard`; views are the frames' own `white`/`black` strings. Stockfish depth 12 (`bots/eBotI/stockfish/src/stockfish`), cp from the mover's point of view, mate clipped to +-3000; `gap` = cp of Stockfish's top move minus cp of the played move (searched with `root_moves`). Positions illegal for Stockfish (side not to move in check) were skipped; a played move that is illegal in standard chess (own king left attackable) counts as -3000. Scripts in `gg2/bait/`: `extract.py` (per-move features, `moves.pkl`), `sf.py` (jobs + 2 engines, `sf_0.pkl`, `sf_1.pkl`), `report.py` -> `report_raw.md` (all tables, reproduced in the appendix).

## 1. The bait moves are Stockfish's moves

39 of Greek Gift's 168 king-capture wins end with a move that put the moved piece on a square the loser attacked (the earlier report counted 40 with a slightly different filter). Bait pieces: Q 21, R 9, P 6, N 2, B 1.

- **Gap to Stockfish's top move: median 0 cp. 30/39 the bait IS the top move; 37/39 within 30 cp; 38/39 within 80 cp.** The one outlier (if83zwbh, Rh1h7 instead of b2b3, gap 188) is still +417 for Greek Gift. In 31/39 Stockfish scores the bait as forced mate on the true board (a queen on g7/h7/b2 etc. protected by a rook or bishop the loser cannot see). On the true board these are not sacrifices at all: the capture is illegal in standard chess (the king cannot take a protected piece), so Stockfish sees the "protector" and rates the move as mate. Nothing here requires knowing what the opponent sees.
- Greek Gift itself could see the enemy attacker at decision time in only 6/39 cases. In 33/39 it moved next to a king (or onto a square) it could not see; it knew the king's location from belief, not from vision. That is a belief question, not an opponent-model question.

Full per-bait table (Stockfish top, cp, loser's view, replies) in the appendix.

## 2. What the loser saw and could have done

- The piece(s) able to capture the king after the loser's fatal move were **all hidden from the loser in 31/39** (its view string had '?' on their squares). In 7 of the other 8 the only attacker was the bait piece itself (in 9dd5ufq0 a seen queen plus a hidden rook and pawn): the loser did not take it; it played an unrelated move (6) or stepped its king onto another attacked square (2) and was captured by the piece it could see, e.g. enti5chy Be7a3 with Qg7 in sight.
- The loser captured the bait with its fatal move in 26/39 (with the king in 22 of them).
- **Under FoW rules the loser was simply lost in 22/39: no move at all left its king unattackable.** In the remaining 17 it had a safe reply (one that leaves the king unattacked): in 10 of those Stockfish rates the best safe reply as still lost to a forced mate, in 6 it is -800 to -990 cp, and in one (if83zwbh) -465 cp; the loser was already down 8+ points in all of them. Capturing the bait was safe in only 2/39 (1sw9k66h Nf6 could be taken by Qd8xf6; flr3hh1v Pd4 could be taken by c3xd4; the losers did something else).
- So the bait is not a gamble on blindness: in 22 cases it is mate, and in the other 17 the alternative was a lost position anyway. The loser's blindness only decides *how fast* it loses.

## 1b. Tempting landings in general

A "tempting landing" = the mover's piece lands on a square attacked by an enemy piece the mover can see, and the attacker is cheaper than the piece or the square looks undefended from the enemy's view.

| bot | n | gap <30 | 30-79 | 80-199 | 200-499 | >=500 | median gap | defended only by hidden pieces | enemy captured it next | ...and hung its king doing so | enemy hung its king within 1 ply |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Greek Gift | 269 | 192 | 35 | 28 | 11 | 3 | 0 | 175 | 158 | 3 | 5 |
| MMC v4 | 233 | 150 | 26 | 33 | 17 | 7 | 0 | 156 | 136 | 2 | 2 |

Same picture: 84% of Greek Gift's tempting landings are within 80 cp of Stockfish (we: 76%). Where they are not (42 moves, listed in the appendix), they are mostly pawn pushes into a visible pawn's attack (e5, d5, h5, g4, a4...) that Stockfish rates 100-250 cp worse, i.e. ordinary over-aggressive engine-at-low-depth moves, not traps: the enemy took them in 20/42 and never lost its king for it. The 3 cases where the capture of a tempting piece cost the opponent its king are the real "gifts" in the sample and all three are Stockfish top moves.

Landings on attacked squares in the 60-game samples, split by whether the mover could see the attacker:

| bot | attacker seen? | n | gap<30 | 80+ | median gap | enemy took it | ...and hung its king |
|---|---|---|---|---|---|---|---|
| Greek Gift | yes | 58 | 35 | 13 | 18 | 26 | 0 |
| Greek Gift | no | 298 | 180 | 71 | 6 | 91 | 9 |
| MMC v4 | yes | 66 | 38 | 22 | 14 | 27 | 1 |
| MMC v4 | no | 356 | 206 | 85 | 15 | 114 | 1 |

The 9 "enemy took it and hung its king" cases for Greek Gift are all landings next to an unseen king (baits by belief, Stockfish-approved). We get the same situations (356 blind landings) but our opponents hang their king on them once. That difference is about *which squares* the piece lands on (next to the king, with a hidden protector), which the engine on a correct belief produces, and about the opponents' quality.

## 3. Where Greek Gift deviates from Stockfish, what does it get?

60 random Greek Gift games (2723 of its moves evaluated) and 60 of ours (2523 moves).

| | Greek Gift | MMC v4 |
|---|---|---|
| played Stockfish's top move | 43.2% | 49.1% |
| gap >= 80 cp ("Stockfish-losing") | 19.5% (532) | 20.5% (516) |
| gap >= 500 | 45 | 76 |
| median / mean gap | 10 / 59 | 2 / 79 |
| own king left attackable | 6 | 23 |
| losing moves where Stockfish's top is a forced mate it missed | 17 (3%) | 9 (2%) |
| losing moves where top cp >= +500 (already crushing, deviation costs nothing) | 274/532 (52%) | 186/516 (36%) |
| losing moves where top cp <= 0 (deviation in a bad position) | 66 (12%) | 190 (37%) |

By ply band Greek Gift agrees with Stockfish 49% at plies 1-40, 42% at 41-60, 36-37% after; our agreement is 53-57% early, 41-47% late. Greek Gift's "losing" moves are concentrated where it is already winning big (52%); ours are concentrated where we are already losing (37%), which is what a weaker belief looks like, not a different intent.

Classification of the >= 80 cp moves (share of losing moves; losing rate within the class):

| class | Greek Gift | MMC v4 |
|---|---|---|
| quiet move to a square no enemy piece sees | 45% (20% of such moves are losing) | 41% (22%) |
| quiet retreat | 17% (30%) | 9% (24%) |
| lands on attacked square, attacker unseen | 13% (24%) | 16% (24%) |
| capture | 12% (10%) | 13% (12%) |
| king move | 10% (20%) | 14% (17%) |
| lands on attacked square, attacker seen | 2% (22%) | 4% (33%) |
| hangs own king | 1% | 3% |

What the move changes, Stockfish-losing vs Stockfish-fine moves (Greek Gift):

| moves | n | d(own pieces enemy sees) | d(own visible squares) | d(enemy visible squares) | lands unseen | hides a seen piece | moved piece attacks from fog | ...the king | any new fog attack | can attack king from fog next ply |
|---|---|---|---|---|---|---|---|---|---|---|
| losing (>=80) | 532 | +0.03 | +0.25 | -0.33 | 76% | 10% | 31% | 3% | 34% | 14% |
| fine (<80) | 2191 | -0.12 | +0.83 | -1.00 | 74% | 12% | 27% | 3% | 32% | 13% |
| = Stockfish top | 1175 | -0.22 | +1.15 | -1.65 | 66% | 17% | 28% | 4% | 36% | 16% |

Where Greek Gift accepts a Stockfish loss it does **not** get fewer pieces seen (+0.03 vs -0.22 when it plays the engine move), not more vision (+0.25 vs +1.15), not more hiding (10% vs 17%), and only marginally more fog attacks (31% vs 28%) or next-ply unseen king threats (14% vs 16%). The same table for us is the same shape (+0.10 / +0.71 / 9% / 26% / 16%). The deviations are consistent with a shallower or belief-averaged search, not with a blindness objective. The 25 largest non-suicidal deviations (appendix) are missed mates and missed material wins in positions it was already winning by 6-12 points, typically a quiet queen or rook move in the endgame when it does not know where the king is.

## 4. Attacks from the fog

A move "attacks from the fog" when the moved piece, on its new square, attacks an enemy piece or king and the enemy's view has '?' on that square.

| side | moves | moved piece attacks from fog | ...targets the king | any new (unseen attacker, target) pair | fog share of all attacking moves |
|---|---|---|---|---|---|
| Greek Gift | 8110 | 26.1% | 2.6% | 30.9% | 58% |
| GG's opponents | 8185 | 21.9% | 0.5% | 25.6% | 52% |
| MMC v4 | 5858 | 24.1% | 2.2% | 28.7% | 51% |
| MMC's opponents | 5865 | 25.2% | 1.7% | 29.5% | 57% |

Greek Gift attacks from the fog a bit more than its opponents (26% vs 22%; by ply band 30-31% vs 23-25% in plies 21-80) and its king attacks from the fog are 5x its opponents' rate, but we are at 24% / 2.2%, so this is not what separates it from us.

**Against Stockfish's top move from the same positions (sample):**

| bot | positions | played: fog attack | SF top: fog attack | played: king from fog | SF top: king from fog | played lands unseen | SF top lands unseen | own pieces seen after: played / SF top | positions played != top: played fog / top fog |
|---|---|---|---|---|---|---|---|---|---|
| Greek Gift | 2717 | 27.4% | **31.7%** | 2.8% | **3.6%** | 74.3% | 68.3% | 1.45 / 1.50 | 27.2% / 33.8% |
| MMC v4 | 2499 | 25.0% | **32.2%** | 2.1% | **3.8%** | 71.1% | 74.1% | 1.38 / 1.34 | 24.0% / 35.7% |

Stockfish's top-1 move would attack from the fog more often than Greek Gift does (31.7% vs 27.4%), and would attack the king from the fog more often (3.6% vs 2.8%). Greek Gift does not seek unseen attacks beyond what the engine produces; if anything it under-delivers them, exactly as we do. Its one small systematic difference from the engine is that it lands on squares the enemy does not see 6 points more often than Stockfish's choice (74% vs 68%), while for us it is the reverse (71% vs 74%); the effect on how many of its pieces the enemy sees is nil (1.45 vs 1.50).

## Conclusion

- The "Greek gift" is a full-information mate or a protected piece that the loser cannot see is protected. Stockfish on the true board plays the same move (30/39 exactly, 37/39 within 30 cp, 31/39 scored as forced mate). In 22/39 the loser had no safe move at all; in the other 17 its best safe move was still mated (10) or -465 to -990 cp.
- Over 2700 sampled moves Greek Gift matches Stockfish's top move 43% of the time (we: 49%), with the same share of >= 80 cp deviations (19.5% vs 20.5%) and the same classes of deviation. Its deviations buy no vision or concealment, and Stockfish's own move would attack from the fog more often than it does.
- Its play therefore does not need an opponent-blindness model. A full-information engine run on a belief that puts the enemy king and pieces in the right places reproduces it. What it does better than us, consistent with the earlier reports, is upstream: it is ahead more often by ply 40-60 (its engine deviations happen at +500 or more, ours at <= 0), it knows where the king is well enough to land a protected queen next to it, and its opponents hang their king on blind landings 9 times in 60 games versus once for ours. The lever is belief quality (where are the king and the pieces) and the positions reached, not modelling what the opponent sees.

Appendix: full output of `report.py` follows.

---

# Greek Gift: bait, blindness and attacks from the fog

Stockfish depth 12 on the true board; cp from the mover's point of view, mate = +-3000 (clipped). gap = top move cp minus played move cp. A move that is illegal in standard chess (own king left attackable) counts as -3000.

## 1. The 39 bait wins: is the bait a Stockfish move?

39 wins where Greek Gift's last move landed on a square the loser attacked.

| game | opp | ply | bait | SF status | SF top | top cp | bait cp | gap | GG saw attacker | defended (truth / loser's view) | hidden defenders | loser's fatal move | took bait | king attacker(s) at the end, seen by loser? | loser: SF top reply (cp) | safe replies | best safe (cp) | taking bait safe? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| enti5chy | Farsight | 47 | Qg4g7 | ok | g4g7 | 3000 | 3000 | 0 | False | True / True | - | Be7a3 | False | Qg7:seen | None (-3000) | 0/40 | None (n/a) | False (1 capt.) |
| cmpp8ys6 | Knight Vision | 46 | Ba4c2 | ok | a4c2 | 715 | 715 | 0 | False | True / False | c8 | Kb1c2 | True | Rc8:HIDDEN | b1a1 (-831) | 2/35 | b1a1 (-808) | False (1 capt.) |
| m9ajv66u | Knight Vision | 37 | Nc3d5 | ok | c3d5 | 820 | 820 | 0 | True | False / False | - | Pe6d5 | True | Bh3:HIDDEN | d7c6 (-851) | 19/24 | d7c6 (-837) | False (1 capt.) |
| walh5fg4 | TA Baseline S | 129 | Qe7g7 | ok | e7g7 | 3000 | 3000 | 0 | False | True / False | h6 | Nc6e5 | False | Qg7:seen | None (-3000) | 0/11 | None (n/a) | False (1 capt.) |
| if83zwbh | Lost Signal | 47 | Rh1h7 | ok | b2b3 | 605 | 417 | 188 | False | True / False | c7 | Kg8h7 | True | Rc7:HIDDEN | b5b2 (-471) | 19/23 | b5b2 (-465) | False (1 capt.) |
| 9dd5ufq0 | Cranberry Lemon | 93 | Pg7g8q | ok | e8h8 | 3000 | 3000 | 0 | False | True / False | g1 e8 | Kh7g6 | False | Rg1:HIDDEN, Ph5:HIDDEN, Qg8:seen | None (-3000) | 0/12 | None (n/a) | False (1 capt.) |
| pdi24olq | Foggy Fischer | 59 | Qc3h8 | ok | c3h8 | 3000 | 3000 | 0 | False | True / False | e8 | Kh7h8 | True | Re8:HIDDEN | None (-3000) | 0/20 | None (n/a) | False (1 capt.) |
| z44ms7od | Gravel Road | 43 | Rf7h7 | ok | f7h7 | 3000 | 3000 | 0 | False | True / False | f6 | Pe5e4 | False | Rh7:seen | None (-3000) | 0/30 | None (n/a) | False (1 capt.) |
| 3mopgvdg | Decent Chess Bot | 95 | Re8e5 | ok | g1g2 | 888 | 839 | 49 | False | True / False | f4 | Kf6e5 | True | Pf4:HIDDEN | a6a5 (-842) | 3/10 | a6a5 (-812) | False (1 capt.) |
| 50h61idz | Team 319 | 55 | Qg4g7 | ok | g4g7 | 3000 | 3000 | 0 | False | True / False | g3 | Kh7g7 | True | Rg3:HIDDEN | None (-3000) | 0/36 | None (n/a) | False (1 capt.) |
| aale3n6g | Mist Opportunities | 45 | Rh4h8 | ok | h4h8 | 3000 | 3000 | 0 | False | True / False | h1 | Kg8h8 | True | Rh1:HIDDEN | None (-3000) | 0/27 | None (n/a) | False (1 capt.) |
| zeqngvbw | TA Baseline A | 48 | Qc8c2 | ok | c8c2 | 3000 | 3000 | 0 | False | True / False | e2 f5 | Kb1c2 | True | Re2:HIDDEN, Bf5:HIDDEN | b1a1 (-3000) | 2/26 | b1a2 (-3000) | False (1 capt.) |
| c2jc2117 | TA Baseline A | 37 | Qh6h7 | ok | h6f8 | 3000 | 3000 | 0 | False | True / False | h1 | Kh8h7 | True | Rh1:HIDDEN | None (-3000) | 0/27 | None (n/a) | False (1 capt.) |
| hupeig41 | Knight Vision | 57 | Qa7b8 | ok | a7c7 | 3000 | 3000 | 0 | False | True / False | a6 | Kc8b8 | True | Na6:HIDDEN | None (-3000) | 0/26 | None (n/a) | False (1 capt.) |
| pix5nxro | Resting Bishop Faces | 98 | Qh5h2 | ok | h5h6 | 886 | 930 | -44 | False | True / False | g4 | Kg1h2 | True | Ng4:HIDDEN | g1f1 (-910) | 1/23 | g1f1 (-986) | False (1 capt.) |
| 0fk2j5gy | Resting Bishop Faces | 39 | Qe6b6 | ok | e6b6 | 3000 | 3000 | 0 | True | False / False | - | Nd7b6 | True | Rd1:HIDDEN | None (-3000) | 0/25 | None (n/a) | False (1 capt.) |
| 4zxokkwy | HYPOTHERMIA | 100 | Qh3g2 | ok | h3g2 | 3000 | 3000 | 0 | False | True / False | e2 | Kg1g2 | True | Re2:HIDDEN | None (-3000) | 0/20 | None (n/a) | False (1 capt.) |
| flr3hh1v | Cranberry Lemon | 208 | Pd5d4 | ok | a4a3 | 1162 | 3000 | -1838 | False | False / False | - | Kf3f2 | False | Rb2:HIDDEN | c3c4 (-3000) | 5/12 | c3c4 (-3000) | True (1 capt.) |
| jhl930ap | Cranberry Lemon | 75 | Rf8h8 | ok | f8h8 | 3000 | 3000 | 0 | False | True / False | e8 | Kh7h8 | True | Re8:HIDDEN | None (-3000) | 0/7 | None (n/a) | False (1 capt.) |
| pf0q73fp | IAmAVirus | 84 | Qf2g1 | ok | f2g1 | 3000 | 3000 | 0 | False | True / False | d4 | Kh1g1 | True | Bd4:HIDDEN | None (-3000) | 0/28 | None (n/a) | False (1 capt.) |
| 8o58b0xu | Unicorns | 72 | Qb8b2 | ok | b8b2 | 3000 | 3000 | 0 | False | True / False | c3 | Kc1b1 | False | Qb2:seen | None (-3000) | 0/35 | None (n/a) | False (1 capt.) |
| 77ciwcob | Unicorns | 53 | Re4e7 | ok | e4e7 | 977 | 977 | 0 | False | True / False | e2 | Kf8e7 | True | Qe2:HIDDEN | d7e5 (-951) | 26/28 | d7e5 (-930) | False (1 capt.) |
| sgtr9bke | TA Baseline S | 78 | Qh4h3 | ok | h4h3 | 3000 | 3000 | 0 | False | True / False | g4 | Kg2g1 | False | Ra1:HIDDEN | None (-3000) | 0/11 | None (n/a) | False (1 capt.) |
| z0aig98o | Foggy Fischer | 88 | Qa8h1 | ok | a8h1 | 3000 | 3000 | 0 | False | True / False | e1 | Kh2h1 | True | Re1:HIDDEN | None (-3000) | 0/7 | None (n/a) | False (1 capt.) |
| vin1lsu8 | Team 319 | 129 | Pd4d5 | ok | g5g8 | 3000 | 3000 | 0 | True | True / False | g5 | Kh8g7 | False | Qg5:HIDDEN | h8h7 (-3000) | 1/6 | h8h7 (-3000) | False (1 capt.) |
| krq6rza6 | Knight Vision | 64 | Qf1g2 | ok | f1g2 | 3000 | 3000 | 0 | False | True / False | e1 | Kh1g2 | True | Ne1:HIDDEN | None (-3000) | 0/24 | None (n/a) | False (1 capt.) |
| 1sw9k66h | Fogitos | 41 | Ne8f6 | ok | e8f6 | 1054 | 1054 | 0 | True | True / False | h4 | Pb5b4 | False | Nf6:seen | d8f6 (-941) | 4/38 | d8f6 (-921) | True (2 capt.) |
| fs6589vu | Farsight | 69 | Pf2f4 | ok | f2f4 | 3000 | 3000 | 0 | False | True / False | g3 | Kg5g4 | False | Kg3:HIDDEN | g5f6 (-3000) | 1/16 | g5f6 (-3000) | False (1 capt.) |
| ml45n8rm | Mist Opportunities | 33 | Rg5g7 | ok | g5g7 | 3000 | 3000 | 0 | False | True / False | g1 | Kg8g7 | True | Rg1:HIDDEN | g8f8 (-3000) | 2/25 | g8f8 (-3000) | False (1 capt.) |
| nb0p6sxv | HYPOTHERMIA | 82 | Pb4c3 | ok | b4c3 | 995 | 995 | 0 | False | True / False | g7 | Pb2c3 | True | Rb7:HIDDEN | b3c4 (-1077) | 5/9 | b3c2 (-3000) | False (2 capt.) |
| adcvfumo | Cranberry Lemon | 141 | Qh7e7 | ok | h7e7 | 3000 | 3000 | 0 | False | True / False | g5 | Ke6f5 | False | Ke4:HIDDEN | None (-3000) | 0/9 | None (n/a) | False (1 capt.) |
| n6rpnbnm | Cranberry Lemon | 55 | Qd7f7 | ok | d7f7 | 3000 | 3000 | 0 | False | True / False | c7 | Kg7f7 | True | Rc7:HIDDEN | g7h8 (-3000) | 1/18 | g7h8 (-3000) | False (1 capt.) |
| sqv3g1zp | TA Baseline S | 56 | Rc1c5 | ok | c1c5 | 3000 | 3000 | 0 | True | False / False | - | Pb4c5 | True | Bd2:HIDDEN | None (-3000) | 0/9 | None (n/a) | False (1 capt.) |
| sv1hfm94 | Next | 104 | Qb7f3 | ok | b7f3 | 3000 | 3000 | 0 | False | True / False | d1 | Kg2f3 | True | Qd1:HIDDEN | g2h2 (-3000) | 1/17 | g2h2 (-3000) | False (1 capt.) |
| mzn083dm | Resting Bishop Faces | 68 | Qb4b2 | ok | b4a4 | 3000 | 3000 | 0 | False | True / False | b7 | Ka2b2 | True | Rb7:HIDDEN | None (-3000) | 0/18 | None (n/a) | False (1 capt.) |
| 28ovw8g6 | Crimson Fog | 63 | Qd7b7 | ok | d7b7 | 3000 | 3000 | 0 | False | True / False | g7 | Kb6b7 | True | Rg7:HIDDEN | b6a5 (-3000) | 1/11 | b6a5 (-3000) | False (1 capt.) |
| ysrf7il4 | IAmAVirus | 37 | Qc2h7 | ok | c2h7 | 3000 | 3000 | 0 | False | True / False | h1 | Pc4c3 | False | Qh7:seen | None (-3000) | 0/40 | None (n/a) | False (1 capt.) |
| 1uze0bcp | RATIRL | 43 | Rd8a8 | ok | d8a8 | 3000 | 3000 | 0 | False | True / False | g8 | Ka7a8 | True | Rg8:HIDDEN | a7b6 (-3000) | 1/17 | a7b6 (-3000) | False (1 capt.) |
| 2kb5hu9d | Strongly Invisible | 325 | Ph7h8q | ok | h7h8q | 3000 | 3000 | 0 | False | True / True | - | Pe4e3 | False | Qh8:seen | None (-3000) | 0/23 | None (n/a) | False (1 capt.) |

- gap distribution of the bait moves: Counter({'<30': 37, '80-199': 1, '30-79': 1}); median gap 0 cp; bait was Stockfish's top move or within 30 cp in 37/39, within 80 cp in 38/39.
- the piece(s) that could capture the king at the end were all hidden from the loser in 31/39 baits; the loser took the bait with its fatal move in 26/39.
- the loser had at least one safe reply (king not attackable afterwards) in 17/39; capturing the bait was safe in 2/39.

## 1b. All tempting landings (piece lands on a square attacked by an enemy piece the mover can see, and the attacker is cheaper or the square looks undefended to the enemy)

| bot | n | SF ok | gap <30 | 30-79 | 80-199 | 200-499 | >=500 | median gap | only hidden defenders | enemy captured it next | ...and hung its king doing so | enemy died within 2 plies |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Greek Gift | 269 | 269 | 192 | 35 | 28 | 11 | 3 | 0 | 175 | 158 | 3 | 5 |
| MMC v4 | 233 | 233 | 150 | 26 | 33 | 17 | 7 | 0 | 156 | 136 | 2 | 2 |

All non-capture landings on enemy-attacked squares in the 60-game samples, by whether the mover could see an attacker at decision time:

| bot | attacker seen? | n | gap<30 | 30-79 | 80-199 | 200-499 | >=500 | median gap | bait attacks king | enemy took it next | ...and hung its king | enemy hung king next move (any) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Greek Gift | True | 58 | 35 | 10 | 6 | 4 | 3 | 18 | 2 | 26 | 0 | 1 |
| Greek Gift | False | 298 | 180 | 47 | 46 | 21 | 4 | 6 | 15 | 91 | 9 | 10 |
| MMC v4 | True | 66 | 38 | 6 | 15 | 5 | 2 | 14 | 6 | 27 | 1 | 1 |
| MMC v4 | False | 356 | 206 | 65 | 49 | 24 | 12 | 15 | 37 | 114 | 1 | 4 |

Greek Gift's tempting landings that Stockfish rates >= 80 cp worse than its top move:

| game | ply | move | SF top | gap | min attacker | defended truth/view | hidden def | enemy reply | enemy took | enemy hung king | outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cmpp8ys6 | 32 | Pe6e5 | d8a5 | 247 | 1 | True/False | c6 d6 f6 | Nf4d5 | False | False | win |
| m9ajv66u | 23 | Nh3g5 | e1c1 | 257 | 1 | True/False | e3 h5 | Bf8g7 | False | False | win |
| m9ajv66u | 35 | Pa3a4 | h3e6 | 182 | 1 | True/False | a1 c3 | Pb5b4 | False | False | win |
| walh5fg4 | 41 | Ph4h5 | f4e6 | 106 | 1 | True/False | f4 g4 | Ph7h6 | False | False | win |
| d6iwp3pn | 25 | Pg2g4 | e3d4 | 153 | 3 | True/False | h3 | Qd6c6 | False | False | win |
| ldwyip4h | 112 | Ph4h3 | d3f5 | 160 | 1 | False/False | - | Pg2h3 | True | False | win |
| alasn4zh | 73 | Re1e8 | c8h3 | 345 | 9 | True/False | c8 | Qg8e8 | True | False | win |
| 9kzu5eir | 16 | Pe7e5 | d5a5 | 112 | 1 | True/False | d5 g7 | Ne2c3 | False | False | loss |
| 7yrrmn79 | 12 | Pe7e5 | g8f6 | 101 | 1 | True/False | c6 | Pe2e3 | False | False | loss |
| 7yrrmn79 | 56 | Pd5d4 | e3f1 | 128 | 3 | False/False | - | Nc2d4 | True | False | loss |
| l3qqr2x9 | 62 | Qd7d4 | d7f5 | 127 | 3 | False/False | - | Be5d4 | True | False | win |
| 3mopgvdg | 65 | Ph2h3 | c2c6 | 141 | 1 | True/False | g2 | Pg4h3 | True | False | win |
| 3mopgvdg | 71 | Pe3f4 | g3f5 | 93 | 3 | False/False | - | Qe6h3 | False | False | win |
| toqmp7ys | 69 | Bd3f5 | g2g3 | 141 | 1 | False/False | - | Kg7g8 | False | False | win |
| c2jc2117 | 13 | Bc1d2 | c3e4 | 777 | 3 | True/False | d1 e1 f3 | Ne4d2 | True | False | win |
| qbo1yj47 | 41 | Nd5e7 | e2h5 | 156 | 3 | False/False | - | Rb6b2 | False | False | win |
| sgzkj0br | 76 | Pf7f6 | c3d3 | 734 | 1 | True/False | g7 | Pa2a4 | False | False | win |
| sgzkj0br | 78 | Pf6e5 | c3d3 | 383 | 3 | True/False | g7 | Pa4b5 | False | False | win |
| 8u0q457t | 13 | Nc3e4 | c3d5 | 95 | 1 | True/False | d3 | Pd5e4 | True | False | win |
| an8d2x1u | 17 | Pa2a4 | a1b1 | 90 | 1 | True/False | a1 | Pb5b4 | False | False | win |
| op91ma6t | 89 | Pe5e6 | c7e7 | 125 | 1 | False/False | - | Rb8f8 | False | False | win |
| ft59z06p | 38 | Bc8f5 | a7a6 | 152 | 3 | True/False | g6 | Bd3f5 | True | False | win |
| pf0q73fp | 22 | Pc6d5 | e5f3 | 115 | 1 | True/False | f6 | Nc3d5 | True | False | win |
| eojmhrke | 18 | Pd7d5 | h7h6 | 135 | 1 | True/False | a5 c6 e6 f6 | Nc3d5 | True | False | win |
| i4koxbx9 | 23 | Ng5h7 | d3g6 | 338 | 3 | True/False | d3 | Nf6h7 | True | False | win |
| i4koxbx9 | 45 | Qh4g4 | h4f6 | 287 | 1 | False/False | - | Pf5g4 | True | False | win |
| mii45hdx | 36 | Rb8b3 | b8c8 | 107 | 1 | False/False | - | Pa2b3 | True | False | win |
| 3t6vsx3q | 38 | Pc5c4 | a7a6 | 96 | 1 | True/False | d5 c8 | Rc1a1 | False | False | win |
| huj29uxm | 25 | Pc4d5 | d2b3 | 144 | 1 | False/False | - | Pe6d5 | True | False | loss |
| wzc5xwqj | 98 | Pc5c4 | e6e5 | 149 | 1 | True/False | e6 | Qf2e3 | False | False | loss |
| w9y0f38p | 59 | Pe4d5 | g4e6 | 253 | 1 | False/False | - | Rb8b7 | False | False | win |
| jycrrkby | 37 | Pg2g3 | c3b5 | 202 | 3 | True/False | f2 h3 f4 | Bh4e7 | False | False | win |
| ww2ykpkn | 43 | Ph3h4 | f3h5 | 324 | 3 | True/False | e1 | Pf7f6 | False | False | loss |
| 7pijihc6 | 55 | Pb3b4 | d6c5 | 162 | 1 | True/False | c3 | Pa5b4 | True | False | win |
| 7pijihc6 | 57 | Pc3b4 | c3c4 | 108 | 1 | False/False | - | Ka7b6 | False | False | win |
| mzn083dm | 42 | Bc5e3 | e6e2 | 2138 | 3 | True/False | e6 | Bh6e3 | True | False | win |
| wm27pl2o | 28 | Pe6e5 | b6b2 | 238 | 1 | True/False | c6 | Pd4e5 | True | False | win |
| r340htvx | 38 | Pe5e4 | b6c4 | 124 | 1 | True/False | f5 | Pf3e4 | True | False | draw |
| 7ytudhxd | 21 | Pc2c4 | g1f3 | 115 | 3 | True/False | e2 | Bd5b7 | False | False | win |
| ysrf7il4 | 25 | Pd4e5 | d3h7 | 370 | 3 | True/False | c4 | Pf7f5 | False | False | win |
| 4tpo2k9i | 26 | Pg6f5 | b6c6 | 147 | 1 | True/False | c8 | Pe4f5 | True | False | win |
| yhzv7ldc | 43 | Pf5f6 | f3h2 | 140 | 3 | True/False | g5 | Nf8e6 | False | False | win |

## 3. Moves Stockfish rates >= 80 cp below its top move (60-game samples)

### Greek Gift: 2723 evaluated moves in 60 games, 532 (19.5%) at >= 80 cp below top; played SF top move 43.2%; median gap 10; mean gap 59

gap distribution: 200-499: 125, 30-79: 472, 80-199: 362, <30: 1719, >=500: 45

| class | n losing (>=80) | share of losing | n in all moves | losing rate within class | median gap |
|---|---|---|---|---|---|
| quiet move into enemy blind spot | 237 | 45% | 1180 | 20% | 133 |
| retreat (quiet) | 93 | 17% | 308 | 30% | 149 |
| lands on attacked square (attacker unseen) | 71 | 13% | 298 | 24% | 155 |
| capture | 62 | 12% | 605 | 10% | 138 |
| king move | 53 | 10% | 267 | 20% | 123 |
| lands on attacked square (seen attacker) | 13 | 2% | 58 | 22% | 235 |
| hangs own king | 3 | 1% | 6 | 50% | 2167 |

What the move changes (means / shares):

| moves | n | d(own pieces the enemy sees) | d(own visible squares) | d(enemy visible squares) | lands unseen by enemy | hides a seen piece | moved piece attacks from fog | ...attacks king from fog | any new fog attack | can attack king from fog next ply |
|---|---|---|---|---|---|---|---|---|---|---|
| SF-losing (>=80) | 532 | +0.03 | +0.25 | -0.33 | 76% | 10% | 31% | 3% | 34% | 14% |
| SF-losing, king not hung | 529 | +0.03 | +0.25 | -0.34 | 76% | 10% | 31% | 3% | 34% | 14% |
| SF-fine (<80) | 2191 | -0.12 | +0.83 | -1.00 | 74% | 12% | 27% | 3% | 32% | 13% |
| SF top move | 1175 | -0.22 | +1.15 | -1.65 | 66% | 17% | 28% | 4% | 36% | 16% |

### MMC v4: 2523 evaluated moves in 60 games, 516 (20.5%) at >= 80 cp below top; played SF top move 49.1%; median gap 2; mean gap 79

gap distribution: 200-499: 120, 30-79: 373, 80-199: 320, <30: 1634, >=500: 76

| class | n losing (>=80) | share of losing | n in all moves | losing rate within class | median gap |
|---|---|---|---|---|---|
| quiet move into enemy blind spot | 209 | 41% | 943 | 22% | 136 |
| lands on attacked square (attacker unseen) | 85 | 16% | 356 | 24% | 150 |
| king move | 71 | 14% | 406 | 17% | 168 |
| capture | 66 | 13% | 538 | 12% | 146 |
| retreat (quiet) | 46 | 9% | 191 | 24% | 133 |
| lands on attacked square (seen attacker) | 22 | 4% | 66 | 33% | 186 |
| hangs own king | 17 | 3% | 23 | 74% | 2263 |

What the move changes (means / shares):

| moves | n | d(own pieces the enemy sees) | d(own visible squares) | d(enemy visible squares) | lands unseen by enemy | hides a seen piece | moved piece attacks from fog | ...attacks king from fog | any new fog attack | can attack king from fog next ply |
|---|---|---|---|---|---|---|---|---|---|---|
| SF-losing (>=80) | 516 | +0.10 | +0.71 | -0.39 | 67% | 9% | 26% | 1% | 29% | 16% |
| SF-losing, king not hung | 499 | +0.08 | +0.68 | -0.37 | 69% | 9% | 26% | 1% | 29% | 16% |
| SF-fine (<80) | 2007 | -0.09 | +0.84 | -1.01 | 71% | 11% | 25% | 2% | 29% | 12% |
| SF top move | 1239 | -0.19 | +1.02 | -1.47 | 69% | 14% | 26% | 4% | 31% | 13% |

Greek Gift's 25 largest Stockfish losses in the sample that are not king-hangs (what the quiet 'bad' moves look like):

| game | ply | move | class | SF top | top cp | played cp | gap | enemy sees piece before->after | lands unseen | fog attack | d pieces seen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| xw913qgz | 87 | Qh8a8 | quiet move into enemy blind spot | h8d8 | 3000 | 0 | 3000 | False->False | True | P | +0 |
| w9y0f38p | 91 | Qc1b1 | quiet move into enemy blind spot | c1c6 | 3000 | 377 | 2623 | False->False | True | RK | +0 |
| 3gjixu7t | 61 | Rc1c2 | quiet move into enemy blind spot | e4a8 | 3000 | 592 | 2408 | False->False | True | - | +0 |
| 3gjixu7t | 65 | Re1c1 | quiet move into enemy blind spot | e4e8 | 3000 | 619 | 2381 | False->False | True | - | +0 |
| pf0q73fp | 32 | Bc8f5 | lands on attacked square (attacker unseen) | d6h2 | 3000 | 772 | 2228 | False->True | False | - | +0 |
| 3gjixu7t | 63 | Kg2h2 | king move | e4e8 | 3000 | 834 | 2166 | False->False | True | - | +0 |
| alasn4zh | 67 | Qg3g2 | retreat (quiet) | e1e8 | 3000 | 862 | 2138 | False->False | True | - | +0 |
| mzn083dm | 42 | Bc5e3 | lands on attacked square (seen attacker) | e6e2 | 3000 | 862 | 2138 | False->True | False | - | +1 |
| rzi6bgbb | 65 | Rh2h7 | capture | g5f6 | 3000 | 875 | 2125 | False->True | False | - | +1 |
| alasn4zh | 63 | Pf2f3 | lands on attacked square (attacker unseen) | e1e7 | 3000 | 928 | 2072 | False->True | False | - | +1 |
| d6iwp3pn | 57 | Qa7b6 | retreat (quiet) | d1d6 | 3000 | 1151 | 1849 | False->False | True | PBP | +0 |
| an8d2x1u | 89 | Qf8g7 | retreat (quiet) | f8f4 | 3000 | 1193 | 1807 | False->False | True | PK | +0 |
| vin1lsu8 | 125 | Pe3d4 | capture | g5h6 | 3000 | 1244 | 1756 | True->False | True | - | -1 |
| 0askyt3o | 86 | Re8e2 | quiet move into enemy blind spot | c1h1 | 3000 | 1258 | 1742 | False->False | True | P | +0 |
| i4koxbx9 | 43 | Bf6e7 | capture | e1e7 | 3000 | 1280 | 1720 | True->True | False | - | +0 |
| hk5xnaw6 | 66 | Kf7e7 | king move | h5h4 | -1281 | -3000 | 1719 | False->False | True | - | +0 |
| wzc5xwqj | 106 | Kh6g7 | king move | h6g5 | -1304 | -3000 | 1696 | False->False | True | - | +0 |
| d6iwp3pn | 53 | Ra5a4 | lands on attacked square (attacker unseen) | a7a8 | 3000 | 1344 | 1656 | False->True | False | - | +1 |
| ayf6jm7h | 123 | Kd5e6 | king move | a5a6 | 1333 | 0 | 1333 | False->False | True | - | +0 |
| cmgf7d47 | 124 | Qh1h2 | retreat (quiet) | b3b2 | 3000 | 1761 | 1239 | False->False | True | K | +0 |
| 65mo7b3z | 171 | Kh4h5 | king move | f6e4 | 896 | 0 | 896 | False->False | True | P | +0 |
| u6s7qu6m | 102 | Qc7b7 | quiet move into enemy blind spot | c7c3 | 558 | -278 | 836 | True->False | True | - | -1 |
| w9y0f38p | 75 | Be4f3 | retreat (quiet) | d1c1 | 525 | -277 | 802 | False->False | True | R | +0 |
| f8qm6hoi | 96 | Ra8c8 | lands on attacked square (attacker unseen) | f5d6 | 332 | -470 | 802 | False->True | False | - | +1 |
| c2jc2117 | 13 | Bc1d2 | lands on attacked square (seen attacker) | c3e4 | 670 | -107 | 777 | False->True | False | - | +1 |

## 4. Attacks from the fog

A move 'attacks from the fog' when the moved piece, on its new square, attacks an enemy piece or king and the enemy cannot see that square (its square is '?' in the enemy's view after the move). 'new fog attack' counts any new (unseen attacker, target) pair, including discovered ones.

| side | moves | moved piece attacks from fog | ...targets the king | any new fog attack | moved piece attacks (seen or not) | fog share of attacking moves |
|---|---|---|---|---|---|---|
| Greek Gift | 8110 | 2119 (26.1%) | 210 (2.6%) | 2505 (30.9%) | 3665 (45.2%) | 58% |
| GG's opponents | 8185 | 1790 (21.9%) | 45 (0.5%) | 2099 (25.6%) | 3429 (41.9%) | 52% |
| MMC v4 | 5858 | 1410 (24.1%) | 126 (2.2%) | 1680 (28.7%) | 2787 (47.6%) | 51% |
| MMC's opponents | 5865 | 1477 (25.2%) | 101 (1.7%) | 1733 (29.5%) | 2610 (44.5%) | 57% |

Fog-attack rate of the moved piece by ply band:

| ply | Greek Gift | GG opps | MMC v4 | MMC opps |
|---|---|---|---|---|
| 1-20 | 17.5% (1790) | 16.8% (1790) | 16.5% (1494) | 26.5% (1492) |
| 21-40 | 29.6% (1777) | 24.0% (1778) | 29.7% (1406) | 27.3% (1412) |
| 41-60 | 31.0% (1543) | 24.8% (1551) | 27.0% (1188) | 27.2% (1193) |
| 61-80 | 29.9% (1184) | 22.9% (1201) | 22.1% (793) | 24.4% (788) |
| 81-400 | 24.6% (1816) | 21.6% (1865) | 25.5% (977) | 18.2% (980) |

Stockfish comparison (sampled 60 games each; positions where the played move was evaluated):

| bot | positions | played: fog attack | SF top: fog attack | played: fog attack on king | SF top: fog attack on king | played lands unseen | SF top lands unseen | played: own pieces seen after | SF top: own pieces seen after | positions where played != top | among those: played fog / top fog |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Greek Gift | 2717 | 27.4% | 31.7% | 2.8% | 3.6% | 74.3% | 68.3% | 1.45 | 1.50 | 1774 | 27.2% / 33.8% |
| MMC v4 | 2499 | 25.0% | 32.2% | 2.1% | 3.8% | 71.1% | 74.1% | 1.38 | 1.34 | 1528 | 24.0% / 35.7% |

Agreement with Stockfish's top move by ply band (sample):

| ply | GG: n | GG: top-move % | GG: gap>=80 % | GG mean gap | MMC: n | MMC: top-move % | MMC: gap>=80 % | MMC mean gap |
|---|---|---|---|---|---|---|---|---|
| 1-20 | 630 | 49% | 7% | 25 | 600 | 57% | 11% | 32 |
| 21-40 | 621 | 49% | 18% | 39 | 573 | 53% | 23% | 63 |
| 41-60 | 523 | 42% | 26% | 70 | 482 | 46% | 26% | 88 |
| 61-80 | 391 | 37% | 26% | 95 | 327 | 47% | 21% | 101 |
| 81-400 | 558 | 36% | 25% | 83 | 541 | 41% | 24% | 127 |

Stockfish status counts (sample+bait jobs): Counter({'ok': 5277, 'played_illegal_std': 30})
