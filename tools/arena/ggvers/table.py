"""Markdown table of per-version metrics from results.pkl."""
import pickle, sys
D = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/research/ggvers/"
res, pl, rows = pickle.load(open(D + "results.pkl", "rb"))
VERS = [v for v in (1, 2, 14, 16, 21, 25, 30) if v in res]
def f(x, d=2):
    return "-" if x is None else ("%%.%df" % d) % x
def pct(x): return "-" if x is None else "%.0f%%" % (100 * x)
def pct1(x): return "-" if x is None else "%.1f%%" % (100 * x)
L = []
def row(name, fn):
    L.append("| %s | %s |" % (name, " | ".join(fn(v) for v in VERS)))
L.append("| metric | " + " | ".join("v%d" % v for v in VERS) + " |")
L.append("|---|" + "---|" * len(VERS))
row("**Arena (all games)** games", lambda v: str(pl[v]["games (all)"]))
row("score (all)", lambda v: f(pl[v]["score (all)"], 3))
row("vs staff bots: games / score", lambda v: "%d / %s" % (pl[v]["vs staff: games, score"][0], f(pl[v]["vs staff: games, score"][1], 2)))
row("vs non-staff: games / score", lambda v: "%d / %s" % (pl[v]["vs non-staff: games, score"][0], f(pl[v]["vs non-staff: games, score"][1], 3)))
row("common-opp score vs v25's score on same opps (n opps)", lambda v: "%s vs %s (%d)" % (f(pl[v]["common-opp (with v25): n opps, weight, score, v25 score"][2], 3), f(pl[v]["common-opp (with v25): n opps, weight, score, v25 score"][3], 3), pl[v]["common-opp (with v25): n opps, weight, score, v25 score"][0]))
row("share of games vs opps v25 also met", lambda v: pct(pl[v]["share of games vs opponents also met by v25"]))
row("draw share (all) / loss reasons (all)", lambda v: "%s / %s" % (pct1(pl[v]["draw share (all)"]), ", ".join("%s %d" % (k.replace("King capturable", "king").replace("Threefold repetition", "3fold"), n) for k, n in pl[v]["loss reasons (all)"].most_common())))
row("draw reasons (all)", lambda v: ", ".join("%s %d" % (k.replace("Threefold repetition", "3fold").replace("Fifty-move rule", "50mv").replace("Insufficient material", "insuf"), n) for k, n in pl[v]["draw reasons (all)"].most_common()))
row("game length mean (all)", lambda v: f(pl[v]["plies mean (all)"], 0))
row("**Sample** games (W-D-L)", lambda v: "%d (%s)" % (res[v]["games"], res[v]["W-D-L"]))
row("own moves in sample", lambda v: str(res[v]["moves"]))
row("**Time** think mean plies 1-10 / 11-20 / 21-40 / 41-60 / 61+ (s)", lambda v: " / ".join(f(res[v]["think " + k][0], 1) if res[v]["think " + k] else "-" for k in ("1-10", "11-20", "21-40", "41-60", "61+")))
row("think mean all / max (s)", lambda v: "%s / %s" % (f(res[v]["think all mean"], 2), f(res[v]["think max"], 1)))
row("moves under 0.4 s", lambda v: pct1(res[v]["think < 0.4 s share"]))
row("games opening with a <0.4 s move / book length mean, max (own moves)", lambda v: "%s / %s, %d" % (pct(res[v]["games starting with a fast move"]), f(res[v]["book length (own moves) mean/median/max"][0], 1), res[v]["book length (own moves) mean/median/max"][2]))
row("clock at ply 40 / 80 / end, mean (s)", lambda v: "%s / %s / %s" % (f(res[v]["clock at ply 40 mean/median (n)"][0], 0) if res[v]["clock at ply 40 mean/median (n)"] else "-", f(res[v]["clock at ply 80 mean/median (n)"][0], 0) if res[v]["clock at ply 80 mean/median (n)"] else "-", f(res[v]["clock at end mean/median"][0], 0)))
row("games ending under 20 s / clock min (s)", lambda v: "%s / %s" % (pct(res[v]["games ending < 20 s"]), f(res[v]["clock min"], 1)))
row("fit think = a + (clock-r)/max(f, D-s*n): a, r, D, s, f (median err)", lambda v: ("a=%g r=%g D=%g s=%g f=%g (%.2f)" % (res[v]["time fit"][1], res[v]["time fit"][2], res[v]["time fit"][3], res[v]["time fit"][4], res[v]["time fit"][5], res[v]["time fit"][0])) if res[v]["time fit"] else "-")
row("think by clock bucket >120 / 60-120 / 30-60 / <30 s (mean s)", lambda v: " / ".join(f(res[v]["think by clock"].get(k), 1) for k in (">120", "60-120", "30-60", "<30")))
row("opponents' think mean (s)", lambda v: f(res[v]["opp think mean"], 1))
row("**Openings** 1.d4 share as white (n)", lambda v: "%s (%d)" % (pct(res[v]["1.d4 share"]), res[v]["n as W"]))
row("first move as white", lambda v: ", ".join("%s %d" % (m, n) for m, n in res[v]["first move as W"][:3]))
row("first 3 as white (top 3)", lambda v: "; ".join("%s %d" % (m, n) for m, n in res[v]["first 3 as W"][:3]))
row("first move as black (n)", lambda v: ", ".join("%s %d" % (m, n) for m, n in res[v]["first move as B"][:3]) + " (%d)" % res[v]["n as B"])
row("first 3 as black (top 3)", lambda v: "; ".join("%s %d" % (m, n) for m, n in res[v]["first 3 as B"][:3]))
row("distinct first-3 sequences per game, white / black", lambda v: "%s / %s" % (pct(res[v]["distinct first-3 per game as W"]), pct(res[v]["distinct first-3 per game as B"])))
row("think percentiles 10/25/50/75/90 at clock > 120 s", lambda v: "/".join("%.1f" % x for x in res[v]["think percentiles 10/25/50/75/90 (clock>120)"]))
row("**King** king moves share of own moves", lambda v: pct1(res[v]["king moves share"]))
row("king steps onto an attacked square (= loss by king move) per 100 king moves", lambda v: f(res[v]["king into attacked sq per 100 king moves"], 1))
row("king reachable from an unseen square after the move, share of moves / mean such squares", lambda v: "%s / %s" % (pct(res[v]["king exposed to an unseen square, share of moves"]), f(res[v]["king exposure (unseen squares hitting king) mean per move"], 2)))
row("walk-ins (= walked_in losses) per 1000 decisions", lambda v: f(res[v]["walk-ins per 1000 decisions"], 2))
row("losses in sample: walked_in / check_unanswered / other", lambda v: "%d / %d / %d" % (res[v]["losses by kind"].get("walked_in", 0), res[v]["losses by kind"].get("check_unanswered", 0), sum(res[v]["loss reasons"].values()) - sum(res[v]["losses by kind"].values())))
row("checks given per game", lambda v: f(res[v]["checks given per game"], 1))
row("**Material** unseen-capture pts taken / lost per game", lambda v: "%s / %s" % (f(res[v]["unseen capture pts taken/game"], 1), f(res[v]["unseen capture pts lost/game"], 1)))
row("all capture pts taken / lost per game", lambda v: "%s / %s" % (f(res[v]["all capture pts taken/game"], 1), f(res[v]["all capture pts lost/game"], 1)))
row("unseen share of own / opp captures", lambda v: "%s / %s" % (pct(res[v]["unseen share of own captures"]), pct(res[v]["unseen share of opp captures"])))
row("quiet moves onto a square attacked by an unseen piece", lambda v: pct1(res[v]["quiet moves onto unseen-attacked sq share"]))
row("quiet moves en prise to an unseen piece (undefended or cheaper attacker)", lambda v: pct1(res[v]["quiet moves en prise to unseen attacker share"]))
row("moves leaving another piece undefended and attacked by an unseen piece", lambda v: pct1(res[v]["moves leaving a piece hanging to unseen attacker share"]))
row("promotions per game", lambda v: f(res[v]["promotions per game"], 2))
def b40(v):
    w = res[v]["bal at ply 40 in wins mean (n)"]; l = res[v]["bal at ply 40 in losss mean (n)"]
    return "%s (%d) / %s (%d)" % (((f(w[0], 1), w[1]) if w else ("-", 0)) + ((f(l[0], 1), l[1]) if l else ("-", 0)))
row("**Outcomes** balance at ply 40 in wins (n) / losses (n)", b40)
row("ahead at ply 40 share", lambda v: pct(res[v]["ahead at ply 40 share"]))
row("balance at end in wins / losses", lambda v: "%s / %s" % (f(res[v]["bal at end in wins mean (n)"][0], 1) if res[v]["bal at end in wins mean (n)"] else "-", f(res[v]["bal at end in losss mean (n)"][0], 1) if res[v]["bal at end in losss mean (n)"] else "-"))
row("game length mean / median (sample)", lambda v: "%s / %s" % (f(res[v]["game length mean/median"][0], 0), f(res[v]["game length mean/median"][1], 0)))
row("wins of <= 20 plies (sample)", lambda v: str(res[v]["wins <= 20 plies"]))
print("\n".join(L))
print()
# per-opponent scores for the opponents shared by most versions
opps = pl[25]["per opp"]
shared = [o for o in opps if sum(1 for v in VERS if o in pl[v]["per opp"] and len(pl[v]["per opp"][o]) >= 20) >= 5]
shared.sort(key=lambda o: -len(opps[o]))
print("| opponent (score, games) | " + " | ".join("v%d" % v for v in VERS) + " |")
print("|---|" + "---|" * len(VERS))
for o in shared[:10]:
    print("| %s | %s |" % (o, " | ".join(("%.2f (%d)" % (sum(pl[v]["per opp"][o]) / len(pl[v]["per opp"][o]), len(pl[v]["per opp"][o]))) if o in pl[v]["per opp"] else "-" for v in VERS)))

