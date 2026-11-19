import pickle
from collections import Counter, defaultdict
OUT = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/research/material/"
data, moves, games = pickle.load(open(OUT + "calib_rows.pkl", "rb"))
def mean(xs): return sum(xs) / len(xs) if xs else float("nan")
def lb(l): return "0" if l == 0 else "1-3" if l <= 3 else "4-7" if l <= 7 else "8-11" if l <= 11 else "12-15" if l <= 15 else "16+"
LB = ["0", "1-3", "4-7", "8-11", "12-15", "16+"]

print("## exposure per move (view-computable): undefended non-pawn pieces with lines>=L after our move, mean per move; and true-board unseen-attacked undefended pieces")
for k in ("us", "gg"):
    rows = data[k]; M = moves[k]
    und = [r for r in rows if not r["defended"] and r["val"] >= 3]
    print(k, "undefended minor+ per move: %.2f" % (len(und) / M),
          "| with lines>=8: %.2f" % (sum(1 for r in und if r["lines"] >= 8) / M),
          "| lines>=12: %.2f" % (sum(1 for r in und if r["lines"] >= 12) / M),
          "| true unseen-attacked undefended minor+: %.3f" % (sum(1 for r in und if r["true_unseen"] > 0) / M),
          "| true unseen-attacked undefended pawns: %.3f" % (sum(1 for r in rows if not r["defended"] and r["val"] == 1 and r["true_unseen"] > 0) / M),
          "| true hazard pts per move (undef val + def excess): %.2f" % (sum((r["val"] if not r["defended"] else max(0, r["val"] - r["true_min"])) for r in rows if r["true_unseen"] > 0) / M))

print("\n## P(taken by unseen next ply) by lines bucket, undefended pieces, moved vs stayed  (n, rate, pts lost/game)")
for k in ("us", "gg"):
    G = games[k]
    for moved in (True, False):
        for val in ((1,), (3,), (5, 9)):
            rows = [r for r in data[k] if not r["defended"] and r["moved"] == moved and r["val"] in val]
            cells = []
            for b in LB:
                rr = [r for r in rows if lb(r["lines"]) == b]
                cells.append(f"{b}: n={len(rr)} p={mean([r['taken'] for r in rr]):.3f}")
            print(k, "moved" if moved else "stayed", "val", val, " | ".join(cells))

print("\n## P(taken by unseen) by TRUE unseen attack, undefended pieces (oracle)")
for k in ("us", "gg"):
    for moved in (True, False):
        rows = [r for r in data[k] if not r["defended"] and r["moved"] == moved and r["val"] >= 3]
        a = [r for r in rows if r["true_unseen"] > 0]; n = [r for r in rows if r["true_unseen"] == 0]
        print(k, "moved" if moved else "stayed", f"true-attacked: n={len(a)} p={mean([r['taken'] for r in a]):.2f} | not: n={len(n)} p={mean([r['taken'] for r in n]):.4f}")

print("\n## the moved piece: by (capture?, defended?, lines>=8) -> n per game, P(taken unseen), pts lost/g, mean gain over 3 plies incl. our capture")
for k in ("us", "gg"):
    G = games[k]
    rows = [r for r in data[k] if r["moved"]]
    for cap in (True, False):
        for dfd in (False, True):
            for hi in (True, False):
                rr = [r for r in rows if r["cap"] == cap and r["defended"] == dfd and (r["lines"] >= 8) == hi]
                if not rr: continue
                print(f"{k} cap={cap} def={dfd} lines>=8={hi}: n/g={len(rr)/G:.2f} P(taken)={mean([r['taken'] for r in rr]):.3f} lost/g={sum(r['val'] for r in rr if r['taken'])/G:.2f} gain3/g={sum(r['gain'] for r in rr)/G:+.2f} mean gain3={mean([r['gain'] for r in rr]):+.2f}")

print("\n## capture into fog: undefended landing, capturer value vs captured value")
for k in ("us", "gg"):
    G = games[k]
    rows = [r for r in data[k] if r["moved"] and r["cap"] and not r["defended"]]
    for name, cond in (("capturer > captured (e.g. NxP)", lambda r: r["val"] > r["capval"]), ("capturer <= captured", lambda r: r["val"] <= r["capval"])):
        rr = [r for r in rows if cond(r)]
        for hi in (True, False):
            r2 = [r for r in rr if (r["lines"] >= 8) == hi]
            print(f"{k} {name} lines>=8={hi}: n/g={len(r2)/G:.2f} P(taken)={mean([r['taken'] for r in r2]):.3f} taken pts/g={sum(r['val'] for r in r2 if r['taken'])/G:.2f} capval/g={sum(r['capval'] for r in r2)/G:.2f} gain3/g={sum(r['gain'] for r in r2)/G:+.2f} mean gain3={mean([r['gain'] for r in r2]):+.2f}")
    # by value pair
    pairs = defaultdict(list)
    for r in rows: pairs[(r["val"], r["capval"])].append(r)
    print(k, "pairs (capturer,captured): n, P(taken), mean gain3:", {p: (len(v), round(mean([r['taken'] for r in v]), 2), round(mean([r['gain'] for r in v]), 2)) for p, v in sorted(pairs.items()) if len(v) >= 10})

print("\n## quiet moves of undefended minor+ onto lines>=8 squares: n/g, P(taken), pts lost")
for k in ("us", "gg"):
    G = games[k]
    rr = [r for r in data[k] if r["moved"] and not r["cap"] and not r["defended"] and r["val"] >= 3]
    for b in LB:
        r2 = [r for r in rr if lb(r["lines"]) == b]
        print(f"{k} {b}: n/g={len(r2)/G:.2f} P={mean([r['taken'] for r in r2]):.3f} lost/g={sum(r['val'] for r in r2 if r['taken'])/G:.2f}")

print("\n## stayed undefended minor+ (we left them): per bucket n/g, P(taken), lost/g")
for k in ("us", "gg"):
    G = games[k]
    rr = [r for r in data[k] if not r["moved"] and not r["defended"] and r["val"] >= 3]
    for b in LB:
        r2 = [r for r in rr if lb(r["lines"]) == b]
        print(f"{k} {b}: n/g={len(r2)/G:.2f} P={mean([r['taken'] for r in r2]):.3f} lost/g={sum(r['val'] for r in r2 if r['taken'])/G:.2f}")
