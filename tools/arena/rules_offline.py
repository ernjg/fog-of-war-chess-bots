"""Score aggregation rules offline on saved evidence (paired2_*.pkl): same Stockfish scores,
different ways of turning them into a move, judged on the true board."""
import glob, pickle, sys
import numpy as np
R = str(Path(__file__).resolve().parents[2]); sys.path.insert(0, R); sys.path.insert(0, R + "/bots/eBotI")
import fow
from eBotI import stockfish_search as ss
from eBotI.stockfish_search import Evidence
S = os.environ.get("ARENA_CACHE", str(Path(__file__).resolve().parents[2] / "data" / "arena"))
ss.WORST_MIX = 0.0   # the module default is now 0.3; the rules below add it explicitly
recs = []
for f in sorted(glob.glob(S + "/paired2_*.pkl")): recs += pickle.load(open(f, "rb"))
print(len(recs), "decisions")

def evidence(rec):
    e = rec["ev"]
    return Evidence(e["scan_attacked"], e["scan_suicide"], e["root_attacked"], e["root_suicide"], e["root_values"], len(e["root_index"]), (),
                    e["scan_count"], e["scan_count"][e["root_index"]])

def v4(rec, aw=6.0):
    v, r = ss.weigh(evidence(rec), attacked_weight=aw, exact_risk=rec["exact_risk"]); return v

def unweighted_risk(rec):
    e = rec["ev"]; return e["scan_suicide"].mean(axis=0)

def veto(rec, share=1.0):
    """v4, but the king-loss risk is the larger of the belief's share and `share` x the plain share of scanned boards"""
    ev = evidence(rec); risk = np.maximum(rec["exact_risk"], share * unweighted_risk(rec))
    v, _ = ss.weigh(ev, exact_risk=risk); return v

def sf2(rec, mix=0.3, aw=6.0):
    """StrangeFish2: (1-mix) x weighted mean of the board values (king loss = -1) + mix x unweighted worst board"""
    e = rec["ev"]; vals = e["root_values"].copy()
    w = e["scan_count"][e["root_index"]] * np.where(e["root_attacked"], aw, 1.0)
    mean = (w @ vals) / w.sum(); worst = vals.min(axis=0)
    return (1 - mix) * mean + mix * worst

def sf2_exact(rec, mix=0.3):
    """sf2 blend inside v4's risk formula with the exact king-loss risk"""
    e = rec["ev"]; vals = e["root_values"]; w = e["scan_count"][e["root_index"]] * np.where(e["root_attacked"], 6.0, 1.0)
    safe = ~e["root_suicide"]
    mean = np.array([(w[safe[:, a]] @ vals[safe[:, a], a]) / w[safe[:, a]].sum() if safe[:, a].any() else -1.0 for a in range(vals.shape[1])])
    worst = np.array([vals[safe[:, a], a].min() if safe[:, a].any() else -1.0 for a in range(vals.shape[1])])
    r = rec["exact_risk"]; return -r + (1 - r) * ((1 - mix) * mean + mix * worst)

def discipline(rec, pen=0.1):
    """v4 minus a penalty on king moves while the belief says we are probably not in check and we still have pieces"""
    v = v4(rec); e = rec["ev"]; w = e["scan_count"]
    check_share = float(w @ e["scan_attacked"]) / w.sum()
    if check_share < 0.2 and rec["pieces"] >= 5:
        v = v - pen * np.array(rec["king_moves"], float)
    return v

RULES = {"v4": v4, "veto 1.0": veto, "veto 0.5": lambda r: veto(r, 0.5), "sf2 0.3": sf2, "sf2 0.15": lambda r: sf2(r, 0.15),
         "sf2-exact 0.3": sf2_exact, "discipline 0.1": discipline, "discipline 0.05": lambda r: discipline(r, 0.05),
         "sf2-exact 0.3 + disc 0.1": lambda r: sf2_exact(r) - (0.1 * np.array(r["king_moves"], float) if r["pieces"] >= 5 else 0)}
base_moves = {}
print(f"{'rule':26s} {'king lost':>9s} {'fog-attacked':>12s} {'king moves':>10s} {'value lost':>10s} {'changed':>8s} {'better/worse>0.1':>17s} {'=played':>8s}")
for name, rule in RULES.items():
    kl = fa = km = ch = better = worse = same = 0; vl = []
    for i, rec in enumerate(recs):
        v = rule(rec); top = int(np.argmax(v + 1e-9 * np.arange(len(v))))
        tv = rec["true_values"]; known = [x for x in tv if x is not None]; best = max(known) if known else None
        kl += tv[top] == -1.0; fa += rec["fog_after"][top] > rec["fog_before"]; km += rec["king_moves"][top]
        same += rec["moves"][top] == rec["played"]
        if best is not None and tv[top] is not None: vl.append(max(0.0, best - tv[top]))
        if name == "v4": base_moves[i] = top
        else:
            b = base_moves[i]
            if b != top:
                ch += 1
                if tv[top] is not None and tv[b] is not None:
                    better += tv[top] - tv[b] > 0.1; worse += tv[b] - tv[top] > 0.1
    print(f"{name:26s} {kl:9d} {fa:12d} {km:10d} {np.mean(vl):10.4f} {ch:8d} {better:8d}/{worse:<8d} {same:8d}")
