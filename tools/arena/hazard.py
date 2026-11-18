"""Empirical king hazard from our arena games: at every one of our decisions, for the
square our king stands on after our move, how exposed it is to squares we cannot see
(slider rays through unseen squares, knight squares unseen), against whether an unseen
piece actually attacked it (true board). Usage: python hazard.py <team id> <games>"""
import json, subprocess, sys, time, pickle, os
from urllib.parse import quote
from collections import Counter, defaultdict
R = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, R)
import chess, fow
from referee import FowBoard, fow_moves, observation
B = "https://6s890.lids.mit.edu"
team, count = sys.argv[1], int(sys.argv[2])
CACHE = os.environ.get("ARENA_CACHE", str(Path(__file__).resolve().parents[2] / "data" / "arena")) + "/replays_cache.pkl"
cache = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
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
games = [g for g in games[:count] if (g["whiteVersion"] if g["whitePlayerId"] == team else g["blackVersion"]) == 4]
for g in games:
    if g["id"] not in cache:
        rep = api(f"/api/games/{g['id']}")
        if "frames" in rep:
            cache[g["id"]] = rep; pickle.dump(cache, open(CACHE, "wb"))
print(f"{sum(g['id'] in cache for g in games)} of {len(games)} replays", flush=True)

def wins(b):
    k = b.king(not b.turn); return k is None or b.is_attacked_by(b.turn, k)

def exposure(board, obs, sq, us):
    """Unseen squares from which a slider (rook/bishop rays, stopped by any visible piece)
    or a knight could attack `sq`."""
    rook = bishop = 0
    for df, dr in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
        f, r = chess.square_file(sq) + df, chess.square_rank(sq) + dr
        while 0 <= f < 8 and 0 <= r < 8:
            s = chess.square(f, r)
            if obs[s] != "?":   # a seen square: empty '-' lets the ray pass, a piece blocks it
                if obs[s] != "-": break
            else:
                if df == 0 or dr == 0: rook += 1
                else: bishop += 1
            f += df; r += dr
    knight = sum(1 for s in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[sq]) if obs[s] == "?")
    return rook, bishop, knight

buckets = defaultdict(lambda: [0, 0])   # key -> [decisions, attacked by unseen]
rows = []
for g in games:
    if g["id"] not in cache: continue
    rep = cache[g["id"]]; us = chess.WHITE if g["whitePlayerId"] == team else chess.BLACK
    b = FowBoard()
    for f in rep["frames"][1:]:
        mv = chess.Move.from_uci(f["move"])
        if b.turn == us:
            obs_before = observation(b, us)
            after = b.copy(stack=False); after.push(mv)
            k = after.king(us)
            if k is not None:
                # exposure judged from what we saw before moving, with our own move applied to our pieces
                obs = list(obs_before); 
                obs[mv.from_square] = "-"; obs[mv.to_square] = obs_before[mv.from_square]
                rook, bishop, knight = exposure(after, obs, k, us)
                attackers = after.attackers(not us, k)
                unseen_attack = any(obs_before[s] == "?" for s in attackers)
                opp_material = sum(len(after.pieces(pt, not us)) * v for pt, v in ((chess.QUEEN, 9), (chess.ROOK, 5), (chess.BISHOP, 3), (chess.KNIGHT, 3)))
                key = ("rook+queen rays", min(rook, 14) // 3 * 3)
                buckets[key][0] += 1; buckets[key][1] += unseen_attack
                key = ("bishop rays", min(bishop, 13) // 3 * 3)
                buckets[key][0] += 1; buckets[key][1] += unseen_attack
                key = ("all unseen reach", min(rook + bishop + knight, 24) // 4 * 4)
                buckets[key][0] += 1; buckets[key][1] += unseen_attack
                rows.append((rook, bishop, knight, unseen_attack, opp_material))
        b.push(mv)
n = len(rows); hits = sum(r[3] for r in rows)
print(f"{n} of our decisions, king attacked by an unseen piece after {hits} ({100*hits/n:.2f}%)\n")
for kind in ("rook+queen rays", "bishop rays", "all unseen reach"):
    print(kind)
    for key in sorted(k for k in buckets if k[0] == kind):
        d, a = buckets[key]
        print(f"   >= {key[1]:2d}: {d:5d} decisions, attacked {a:3d} ({100*a/max(d,1):5.2f}%)")
# how much does exposure differ between chosen moves and the least exposed alternative? (sample)
pickle.dump(rows, open(os.path.dirname(CACHE) + "/hazard_rows.pkl", "wb"))
