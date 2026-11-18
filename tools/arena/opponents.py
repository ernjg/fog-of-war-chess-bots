"""Our arena record per opponent against what Elo predicts. Usage: python opponents.py <team id> <games>"""
import json, subprocess, sys, time, math
from urllib.parse import quote
from collections import defaultdict
B = "https://6s890.lids.mit.edu"
team, count = sys.argv[1], int(sys.argv[2])
def api(path):
    for a in range(6):
        try:
            d = json.loads(subprocess.run(["curl", "-s", "-m", "60", B + path], capture_output=True, text=True, check=True).stdout)
            if "games" in d or "players" in d:
                time.sleep(1.0); return d
        except Exception:
            pass
        time.sleep(5 * (a + 1))
    return {}
lb = api("/api/leaderboard")
rating = {p["id"]: p["rating"] for p in lb.get("players", []) if p.get("rating") is not None}
names = {p["id"]: p["name"] for p in lb.get("players", [])}
ours = rating.get(team, 1850)
print(f"leaderboard: {len(rating)} players; our rating {ours:.0f}; top 8: " + ", ".join(f"{p['name'][:14]} {p['rating']:.0f}" for p in sorted([p for p in lb["players"] if p.get("rating") is not None], key=lambda p: -p["rating"])[:8]))
games, cursor = [], None
while len(games) < count:
    d = api(f"/api/games?limit=50&sort=played&order=desc&player={team}" + (f"&cursor={quote(cursor, safe='')}" if cursor else ""))
    if "games" not in d: break
    games += d["games"]; cursor = d.get("nextCursor")
    if not cursor: break
rec = defaultdict(lambda: [0, 0, 0, 0.0])  # w, d, l, expected
plies = defaultdict(list)
for g in games[:count]:
    us_white = g["whitePlayerId"] == team
    ver = g["whiteVersion"] if us_white else g["blackVersion"]
    if ver != 4: continue
    opp = g["blackPlayerId"] if us_white else g["whitePlayerId"]
    r = g["result"]; s = 0.5 if r == "1/2-1/2" else (1.0 if (r == "1-0") == us_white else 0.0)
    rec[opp][0 if s == 1 else 1 if s == 0.5 else 2] += 1
    rec[opp][3] += 1 / (1 + 10 ** ((rating.get(opp, 1500) - ours) / 400))
    plies[opp].append(g.get("plies") or g.get("moves") or 0)
rows = sorted(rec.items(), key=lambda kv: -rating.get(kv[0], 0))
tw = td = tl = te = 0
print(f"{'opponent':22s} {'rating':>6s}  W  D  L   score expected  diff")
for opp, (w, d, l, e) in rows:
    n = w + d + l; sc = w + 0.5 * d
    tw += w; td += d; tl += l; te += e
    print(f"{names.get(opp, opp)[:22]:22s} {rating.get(opp, 0):6.0f} {w:2d} {d:2d} {l:2d}   {sc/n:5.2f}    {e/n:5.2f}  {(sc-e)/n:+5.2f}")
n = tw + td + tl
print(f"\nall: {tw}-{td}-{tl}, score {(tw+0.5*td)/n:.3f}, Elo expected {te/n:.3f}")
above = [(w, d, l, e) for opp, (w, d, l, e) in rows if rating.get(opp, 0) > ours]
below = [(w, d, l, e) for opp, (w, d, l, e) in rows if rating.get(opp, 0) <= ours]
for label, grp in (("vs higher rated", above), ("vs lower rated", below)):
    if grp:
        W = sum(x[0] for x in grp); D = sum(x[1] for x in grp); L = sum(x[2] for x in grp); E = sum(x[3] for x in grp); N = W + D + L
        print(f"  {label}: {W}-{D}-{L} score {(W+0.5*D)/N:.3f} expected {E/N:.3f}")
