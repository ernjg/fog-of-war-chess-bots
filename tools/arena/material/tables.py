import pickle, sys
from collections import Counter, defaultdict
OUT = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/research/material/"
res = pickle.load(open(OUT + "rows.pkl", "rb"))
N = {k: len(v) for k, v in res.items()}
def caps(k): return [c for g in res[k] for c in g["caps"]]
def bucket(p): return "1-20" if p <= 20 else "21-40" if p <= 40 else "41-60" if p <= 60 else "61+"
def mean(xs): return sum(xs) / len(xs) if xs else float("nan")

print("## (a) category")
print("| category | us n | us pts/g | us net2/g | gg n | gg pts/g | gg net2/g |")
cats = ["moved_in", "left_fresh", "left_standing", "opened", "none"]
for c in cats:
    row = [c]
    for k in ("us", "gg"):
        cc = [x for x in caps(k) if x["cat"] == c]
        row += [len(cc), "%.2f" % (sum(x["val"] for x in cc) / N[k]), "%.2f" % (sum(x["net2"] for x in cc) / N[k])]
    print("| " + " | ".join(map(str, row)) + " |")
for k in ("us", "gg"):
    cc = caps(k); print(k, "total n", len(cc), "pts/g %.2f net2/g %.2f" % (sum(x["val"] for x in cc) / N[k], sum(x["net2"] for x in cc) / N[k]))

print("\n## moved_in split: our move was a capture (exchange) vs quiet")
print("| side | kind | n | pts/g | net2/g | defended share | free (undefended) n | free pts/g |")
for k in ("us", "gg"):
    for kind, cond in (("capture", lambda x: x["our_cap"]), ("quiet", lambda x: not x["our_cap"])):
        cc = [x for x in caps(k) if x["cat"] == "moved_in" and cond(x)]
        free = [x for x in cc if not x["defended"]]
        print(f"| {k} | {kind} | {len(cc)} | {sum(x['val'] for x in cc)/N[k]:.2f} | {sum(x['net2'] for x in cc)/N[k]:.2f} | {mean([x['defended'] for x in cc]):.2f} | {len(free)} | {sum(x['val'] for x in free)/N[k]:.2f} |")

print("\n## (b) defended vs free, by category (pts/g lost at the capture, net over 2 more plies)")
print("| side | category | free n | free pts/g | free net2/g | defended n | def pts/g | def net2/g |")
for k in ("us", "gg"):
    for c in cats[:4]:
        cc = [x for x in caps(k) if x["cat"] == c]
        f = [x for x in cc if not x["defended"]]; d = [x for x in cc if x["defended"]]
        print(f"| {k} | {c} | {len(f)} | {sum(x['val'] for x in f)/N[k]:.2f} | {sum(x['net2'] for x in f)/N[k]:.2f} | {len(d)} | {sum(x['val'] for x in d)/N[k]:.2f} | {sum(x['net2'] for x in d)/N[k]:.2f} |")

print("\n## net2 distribution: share of unseen captures that were real losses (net2 <= -2) vs even/favourable exchanges")
for k in ("us", "gg"):
    cc = caps(k)
    print(k, "net2<=-2: %d (%.2f pts/g of net2) ; net2 in (-2,0]: %d ; net2>0: %d" % (
        sum(1 for x in cc if x["net2"] <= -2), sum(x["net2"] for x in cc if x["net2"] <= -2) / N[k],
        sum(1 for x in cc if -2 < x["net2"] <= 0), sum(1 for x in cc if x["net2"] > 0)))
    print("  net2/g by category, only net2<=-2:", {c: round(sum(x["net2"] for x in cc if x["cat"] == c and x["net2"] <= -2) / N[k], 2) for c in cats[:4]})

print("\n## (c) material swing: balance before capture and 10 plies later; 'decisive' = bal_before >= -1 and bal_10 <= -3")
print("| side | category | n | mean bal before | mean bal +10 | decisive n | decisive pts/g | in lost games n | in lost games pts/g |")
for k in ("us", "gg"):
    lost_ids = {g["id"] for g in res[k] if g["outcome"] == "loss"}
    for c in cats[:4] + ["ALL"]:
        rows = [(g, x) for g in res[k] for x in g["caps"] if c == "ALL" or x["cat"] == c]
        dec = [x for g, x in rows if x["bal_before"] >= -1 and x["bal_10"] <= -3]
        lg = [x for g, x in rows if g["id"] in lost_ids]
        print(f"| {k} | {c} | {len(rows)} | {mean([x['bal_before'] for g,x in rows]):.1f} | {mean([x['bal_10'] for g,x in rows]):.1f} | {len(dec)} | {sum(x['val'] for x in dec)/N[k]:.2f} | {len(lg)} | {sum(x['val'] for x in lg)/N[k]:.2f} |")

print("\n## (d) piece type (pts/g) and ply bucket (pts/g)")
for k in ("us", "gg"):
    cc = caps(k)
    pt = defaultdict(float); pb = defaultdict(float); ptn = Counter(); 
    for x in cc: pt[x["pt"]] += x["val"] / N[k]; pb[bucket(x["ply"])] += x["val"] / N[k]; ptn[x["pt"]] += 1
    print(k, "piece:", {p: (ptn[p], round(pt[p], 2)) for p in "PNBRQ"}, "| ply:", {b: round(pb[b], 2) for b in ("1-20", "21-40", "41-60", "61+")})
    byc = defaultdict(float)
    for x in cc: byc[(x["cat"], bucket(x["ply"]))] += x["val"] / N[k]
    print("   cat x ply:", {c: [round(byc[(c, b)], 2) for b in ("1-20", "21-40", "41-60", "61+")] for c in cats[:4]})
    byp = defaultdict(float)
    for x in cc: byp[(x["cat"], x["pt"])] += x["val"] / N[k]
    print("   cat x piece:", {c: [round(byp[(c, p)], 2) for p in "PNBRQ"] for c in cats[:4]})
    print("   captured by:", Counter(x["by"] for x in cc))

print("\n## left_*: attacker standing plies; did we see the attacker at our decision (lost sight by our own move)?")
for k in ("us", "gg"):
    cc = [x for x in caps(k) if x["cat"].startswith("left")]
    print(k, "standing plies:", Counter(min(x["standing_plies"], 6) for x in cc), "saw at decision:", Counter(x["saw_at_decision"] for x in cc))
    print("  pre_haz>0 (piece was already in true hazard at decision):", Counter(x.get("pre_haz", 0) > 0 for x in cc))

print("\n## counterfactual at the decision (moved_in): zero-true-hazard alternatives")
for k in ("us", "gg"):
    for c in ("moved_in", "left_fresh", "left_standing", "opened"):
        cc = [x for x in caps(k) if x["cat"] == c and "zero_alt" in x]
        if not cc: continue
        z = [x for x in cc if x["zero_alt"] > 0]
        print(f"{k} {c}: n={len(cc)}, had >=1 zero-hazard move: {len(z)} ({sum(x['val'] for x in z)/N[k]:.2f} pts/g; net2 {sum(x['net2'] for x in z)/N[k]:.2f}), "
              f"median zero_alt {sorted(x['zero_alt'] for x in cc)[len(cc)//2]}, median n_alt {sorted(x['n_alt'] for x in cc)[len(cc)//2]}, "
              f"chosen_haz mean {mean([x['chosen_haz'] for x in cc]):.1f}, min_alt_haz mean {mean([x['min_alt_haz'] for x in cc]):.1f}, "
              f"zero_alt_noncap>0: {sum(1 for x in cc if x['zero_alt_noncap']>0)}")
        print("    fog_lines at target (view-computable):", Counter(min(x["lines"], 8) for x in cc))
