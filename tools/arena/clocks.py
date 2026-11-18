"""How much clock our arena bot leaves unused, per game, and the opponent's rating.
Usage: python clocks.py <team id> <games>"""
import json, subprocess, sys, time
from urllib.parse import quote
B = "https://6s890.lids.mit.edu"
team, count = sys.argv[1], int(sys.argv[2])
def api(path):
    for a in range(6):
        try:
            d = json.loads(subprocess.run(["curl", "-s", "-m", "60", B + path], capture_output=True, text=True, check=True).stdout)
            if "games" in d or "frames" in d:
                time.sleep(1.0); return d
        except Exception:
            pass
        time.sleep(5 * (a + 1))
    return {}
games, cursor = [], None
while len(games) < count:
    d = api(f"/api/games?limit=50&sort=played&order=desc&player={team}" + (f"&cursor={quote(cursor, safe='')}" if cursor else ""))
    if "games" not in d: break
    games += d["games"]; cursor = d.get("nextCursor")
    if not cursor: break
rows = []
for g in games[:count]:
    r = api(f"/api/games/{g['id']}")
    if "frames" not in r: continue
    us_white = g["whitePlayerId"] == team
    ver = g["whiteVersion"] if us_white else g["blackVersion"]
    if ver != 4: continue
    fr = r["frames"]; last = fr[-1]
    ours = last["clocks"][0 if us_white else 1]; theirs = last["clocks"][1 if us_white else 0]
    plies = len(fr) - 1; our_moves = (plies + (1 if us_white else 0)) // 2
    res = g["result"]; outcome = "D" if res == "1/2-1/2" else ("W" if (res == "1-0") == us_white else "L")
    # per-move think times from the clocks
    think = []
    prev = None
    for f in fr[1:]:
        c = f["clocks"][0 if us_white else 1]
        if prev is not None and c < prev: think.append(prev - c + 2.0)
        prev = c
    rows.append((outcome, our_moves, ours, theirs, g["reason"] if "reason" in g else "", sum(think)/max(len(think),1), max(think) if think else 0))
    opp = g["black"] if us_white else g["white"]
    print(f"{outcome} moves={our_moves:3d} our clock left={ours:6.1f}s  opp left={theirs:6.1f}s  mean think={rows[-1][5]:.1f}s max={rows[-1][6]:.1f}s  vs {opp[:20]}", flush=True)
print(f"\n{len(rows)} games; mean clock left: ours {sum(r[2] for r in rows)/len(rows):.1f}s, opponents {sum(r[3] for r in rows)/len(rows):.1f}s")
for o in "WLD":
    rs = [r for r in rows if r[0] == o]
    if rs: print(f"  {o}: {len(rs)} games, mean moves {sum(r[1] for r in rs)/len(rs):.1f}, mean clock left {sum(r[2] for r in rs)/len(rs):.1f}s, mean think {sum(r[5] for r in rs)/len(rs):.1f}s")
