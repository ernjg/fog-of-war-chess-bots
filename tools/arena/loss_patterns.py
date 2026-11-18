"""How do our arena losses end? Which piece took the king, from where, was it visible the
move before, how early, how did the opponent play (captures, checks, queen moves, think time).
Usage: python loss_patterns.py <team id> <games> [max_opp_rating]"""
import json, subprocess, sys, time, pickle, os
from urllib.parse import quote
from collections import Counter, defaultdict
R = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, R)
import chess, fow
from referee import FowBoard, observation
B = "https://6s890.lids.mit.edu"
team, count = sys.argv[1], int(sys.argv[2])
max_rating = float(sys.argv[3]) if len(sys.argv) > 3 else 9999
CACHE = "replays_cache.pkl"
cache = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
def api(path):
    for a in range(6):
        try:
            d = json.loads(subprocess.run(["curl", "-s", "-m", "60", B + path], capture_output=True, text=True, check=True).stdout)
            if "games" in d or "frames" in d or "players" in d:
                time.sleep(1.0); return d
        except Exception:
            pass
        time.sleep(5 * (a + 1))
    return {}
lb = api("/api/leaderboard"); rating = {p["id"]: p["rating"] for p in lb["players"] if p.get("rating") is not None}
games, cursor = [], None
while len(games) < count:
    d = api(f"/api/games?limit=50&sort=played&order=desc&player={team}" + (f"&cursor={quote(cursor, safe='')}" if cursor else ""))
    if "games" not in d: break
    games += d["games"]; cursor = d.get("nextCursor")
    if not cursor: break
PIECE = {chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B", chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}
rows = []
for g in games[:count]:
    us_white = g["whitePlayerId"] == team
    ver = g["whiteVersion"] if us_white else g["blackVersion"]
    if ver != 4: continue
    opp = g["blackPlayerId"] if us_white else g["whitePlayerId"]
    r = g["result"]
    if r == "1/2-1/2" or (r == "1-0") == us_white: continue
    if rating.get(opp, 0) > max_rating: continue
    if g["id"] not in cache:
        rep = api(f"/api/games/{g['id']}")
        if "frames" not in rep: continue
        cache[g["id"]] = rep; pickle.dump(cache, open(CACHE, "wb"))
    rep = cache[g["id"]]
    fr = rep["frames"]; us = chess.WHITE if us_white else chess.BLACK
    board = FowBoard(); opp_caps = opp_checks = opp_queen = opp_moves = 0; opp_think = []
    prev_clock = None
    hist = []
    for f in fr[1:]:
        mv = chess.Move.from_uci(f["move"]); mover = board.turn
        before = board.copy(stack=False)
        if mover != us:
            opp_moves += 1
            if before.piece_at(mv.to_square): opp_caps += 1
            p = before.piece_at(mv.from_square)
            if p and p.piece_type == chess.QUEEN: opp_queen += 1
            c = f["clocks"][1 if us_white else 0]
            if prev_clock is not None: opp_think.append(prev_clock - c + 2)
            prev_clock = c
        hist.append((before, mv, mover))
        board.push(mv)
        if mover != us:
            k = board.king(us)
            if k is None or board.is_attacked_by(not us, k) and False: pass
    # the final move captured our king
    before, mv, mover = hist[-1]
    attacker = before.piece_at(mv.from_square)
    obs = observation(before, us)   # what we saw before their last move (after ours)
    visible = obs[mv.from_square] != "?"
    # our move just before: did it move the king / into the attack?
    ob, omv, _ = hist[-2]
    our_piece = ob.piece_at(omv.from_square)
    king_moved = our_piece is not None and our_piece.piece_type == chess.KING
    # how many of their last 3 moves were by the attacking piece (a raid)?
    raid = sum(1 for (b_, m_, who) in hist[-6::2] if who != us and b_.piece_at(m_.from_square) and b_.piece_at(m_.from_square).piece_type == attacker.piece_type)
    our_moves = len([h for h in hist if h[2] == us])
    rows.append(dict(opp=g["black"] if us_white else g["white"], rating=rating.get(opp, 0), moves=our_moves,
                     attacker=PIECE[attacker.piece_type], frm=chess.square_name(mv.from_square), to=chess.square_name(mv.to_square),
                     visible=visible, king_moved=king_moved, raid=raid,
                     caps=opp_caps / opp_moves, checks=0, queen=opp_queen / opp_moves, think=sum(opp_think) / max(1, len(opp_think)),
                     king_sq=chess.square_name(mv.to_square), castled=False))
    print(f"{rows[-1]['opp'][:18]:18s} {rows[-1]['rating']:4.0f} L in {our_moves:2d} moves: king on {rows[-1]['king_sq']} taken by {rows[-1]['attacker']} from {rows[-1]['frm']} visible={int(visible)} we_moved_king={int(king_moved)} raid={raid} | opp: captures {rows[-1]['caps']:.2f} queen moves {rows[-1]['queen']:.2f} think {rows[-1]['think']:.1f}s", flush=True)
print(f"\n{len(rows)} losses")
print("attacker:", Counter(r["attacker"] for r in rows))
print("attacker visible before their move:", Counter(r["visible"] for r in rows))
print("we moved the king into it:", Counter(r["king_moved"] for r in rows))
print("king square:", Counter(r["king_sq"] for r in rows).most_common(8))
print("moves to loss:", sorted(r["moves"] for r in rows))
print(f"opp mean think {sum(r['think'] for r in rows)/len(rows):.1f}s, queen move share {sum(r['queen'] for r in rows)/len(rows):.2f}")
