"""Loss anatomy per bot over a local tournament folder. Usage: match_anatomy.py <data dir> [botA botB]"""
import glob, json, sys
from pathlib import Path
R = Path("/Users/ernestogomez/Desktop/fog-of-war-chess-bots"); sys.path.insert(0, str(R)); import fow
import chess
from referee import FowBoard, observation
V = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
d = sys.argv[1]
stats = {}
def S(name): return stats.setdefault(name, dict(games=0, wins=0, draws=0, losses=0, walk_in=0, unanswered=0, seen_death=0, moves=0, kmoves=0, fogwalk=0, mat_unseen=0.0, mat_lost=0.0, plies=0, risky_kmoves=0))
for f in sorted(glob.glob(d + "/*.json")):
    g = json.load(open(f)); names = {chess.WHITE: g["white"], chess.BLACK: g["black"]}
    r = g["result"]; frames = g["frames"]
    for side in (chess.WHITE, chess.BLACK):
        s = S(names[side]); s["games"] += 1; s["plies"] += len(frames) - 1
        if r == "1/2-1/2": s["draws"] += 1
        elif (r == "1-0") == (side == chess.WHITE): s["wins"] += 1
        else: s["losses"] += 1
    b = FowBoard()
    for i, fr in enumerate(frames[1:]):
        mv = chess.Move.from_uci(fr["move"]); mover = b.turn; s = S(names[mover])
        obs = observation(b, mover); s["moves"] += 1
        victim = b.piece_at(mv.to_square)
        if victim and victim.color != mover:
            vs = S(names[not mover]); vobs = observation(b, not mover)
            vs["mat_lost"] += V[victim.piece_type]
            if vobs[mv.from_square] == "?": vs["mat_unseen"] += V[victim.piece_type]
        if b.piece_at(mv.from_square).piece_type == chess.KING: s["kmoves"] += 1
        after = b.copy(stack=False); after.push(mv)
        k = after.king(mover)
        in_check_unseen_before = b.king(mover) is not None and any(obs[a] == "?" for a in b.attackers(not mover, b.king(mover)))
        attacked_after = k is not None and bool(after.attackers(not mover, k))
        unseen_after = k is not None and any(obs[a] == "?" for a in after.attackers(not mover, k))
        if attacked_after and i == len(frames) - 2 and r != "1/2-1/2":
            if not unseen_after: s["seen_death"] += 1
            elif in_check_unseen_before: s["unanswered"] += 1
            else: s["walk_in"] += 1
        b.push(mv)
print(f"{'bot':12s} {'games':>5s} {'W-D-L':>10s} {'score':>6s} {'walk-in':>7s} {'unansw':>6s} {'seen':>5s} {'K moves/g':>9s} {'mat lost/g':>10s} {'unseen/g':>8s}")
for name, s in stats.items():
    n = s["games"]
    print(f"{name:12s} {n:5d} {s['wins']:>3d}-{s['draws']}-{s['losses']:<3d} {(s['wins']+s['draws']/2)/n:6.3f} {s['walk_in']:7d} {s['unanswered']:6d} {s['seen_death']:5d} {s['kmoves']/n:9.1f} {s['mat_lost']/n:10.1f} {s['mat_unseen']/n:8.1f}")
