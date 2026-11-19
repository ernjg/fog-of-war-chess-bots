import pickle
from collections import Counter, defaultdict
OUT = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/research/material/"
rows, ng, pri = pickle.load(open(OUT + "rule_rows.pkl", "rb"))
def mean(xs): return sum(xs) / len(xs) if xs else float("nan")
def lb(L): return "<0.25" if L < 0.25 else "0.25-0.5" if L < 0.5 else "0.5-1" if L < 1 else "1-2" if L < 2 else "2-4" if L < 4 else "4+"
LB = ["<0.25", "0.25-0.5", "0.5-1", "1-2", "2-4", "4+"]
print("## mean expected loss L after our move (view-only) and realised loss to unseen captures next ply, per move")
for k in ("us", "gg"):
    r = rows[k]; print(k, "moves", len(r), "mean L %.2f" % mean([x["L"] for x in r]), "realised/move %.3f" % mean([x["lost"] for x in r]), "realised/game %.2f" % (sum(x["lost"] for x in r) / ng[k]))
print("\n## calibration: by L bucket, all moves (n/g, P(lost>0), realised pts/g, mean L)")
for k in ("us", "gg"):
    for b in LB:
        rr = [x for x in rows[k] if lb(x["L"]) == b]
        print(f"{k} L {b}: n/g={len(rr)/ng[k]:.1f} P(lost)={mean([x['lost']>0 for x in rr]):.3f} realised/g={sum(x['lost'] for x in rr)/ng[k]:.2f} mean L={mean([x['L'] for x in rr]):.2f} realised/move={mean([x['lost'] for x in rr]):.2f}")
print("\n## quiet moves only (no capture): same")
for k in ("us", "gg"):
    for b in LB:
        rr = [x for x in rows[k] if lb(x["L"]) == b and not x["cap"]]
        print(f"{k} L {b}: n/g={len(rr)/ng[k]:.1f} P(lost)={mean([x['lost']>0 for x in rr]):.3f} realised/g={sum(x['lost'] for x in rr)/ng[k]:.2f} realised/move={mean([x['lost'] for x in rr]):.2f} gain3 mean={mean([x['gain'] for x in rr]):+.2f}")
print("\n## captures: same")
for k in ("us", "gg"):
    for b in LB:
        rr = [x for x in rows[k] if lb(x["L"]) == b and x["cap"]]
        print(f"{k} L {b}: n/g={len(rr)/ng[k]:.1f} P(lost)={mean([x['lost']>0 for x in rr]):.3f} realised/g={sum(x['lost'] for x in rr)/ng[k]:.2f} capval/g={sum(x['capval'] for x in rr)/ng[k]:.2f} gain3 mean={mean([x['gain'] for x in rr]):+.2f}")

print("\n## the destination square only: undefended moved piece, dest_e*val bucket -> P(the moved piece is taken by unseen)")
for k in ("us", "gg"):
    for cap in (False, True):
        cells = []
        for b in LB:
            rr = [x for x in rows[k] if not x["king"] and not x["dest_def"] and x["cap"] == cap and lb(x["dest_e"] * x["val"]) == b]
            cells.append(f"{b}: n/g={len(rr)/ng[k]:.2f} P={mean([x['lost_is_dest'] for x in rr]):.3f}")
        print(k, "cap" if cap else "quiet", " | ".join(cells))

print("\n## RULE: reject a QUIET move whose L exceeds T when an alternative with L <= T/2 exists (minalt). Flagged/g, pts lost on flagged moves (saved upper bound), their mean gain3 (cost proxy), and how our flagged rate compares with GG's")
for T in (0.5, 1.0, 1.5, 2.0, 3.0):
    for k in ("us", "gg"):
        fl = [x for x in rows[k] if not x["cap"] and not x["king"] and x["L"] > T and x["minalt"] is not None and x["minalt"] <= T / 2]
        base = [x for x in rows[k] if not x["cap"] and not x["king"]]
        print(f"T={T} {k}: flagged/g={len(fl)/ng[k]:.2f} ({100*len(fl)/len(base):.1f}% of quiet moves) lost on flagged/g={sum(x['lost'] for x in fl)/ng[k]:.2f} P(lost)={mean([x['lost']>0 for x in fl]):.3f} mean gain3 flagged={mean([x['gain'] for x in fl]):+.2f} vs unflagged quiet={mean([x['gain'] for x in base if x not in fl]):+.2f}; mean L flagged={mean([x['L'] for x in fl]):.2f} minalt={mean([x['minalt'] for x in fl]):.2f}")
print("\n## same rule applied to CAPTURES with capturer value > captured value (cost side: what we would forgo)")
for T in (1.0, 2.0):
    for k in ("us", "gg"):
        fl = [x for x in rows[k] if x["cap"] and not x["king"] and x["val"] > x["capval"] and x["L"] > T and x["minalt"] is not None and x["minalt"] <= T / 2]
        print(f"T={T} {k}: flagged/g={len(fl)/ng[k]:.2f} lost on flagged/g={sum(x['lost'] for x in fl)/ng[k]:.2f} capval/g={sum(x['capval'] for x in fl)/ng[k]:.2f} mean gain3={mean([x['gain'] for x in fl]):+.2f}")
print("\n## all captures by L: would a tax on captures hurt? (mean gain3 incl. the capture, by L bucket)")
for k in ("us", "gg"):
    print(k, {b: (round(len([x for x in rows[k] if x['cap'] and lb(x['L'])==b])/ng[k],2), round(mean([x['gain'] for x in rows[k] if x['cap'] and lb(x['L'])==b]),2)) for b in LB})
