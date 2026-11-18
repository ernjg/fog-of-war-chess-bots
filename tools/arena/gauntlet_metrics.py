"""Per configuration, over the local games against v3: score, and the event counts that
decide fog-of-war games (king lost to an unseen attacker, material lost to unseen attackers,
king moves). Usage: python gauntlet_metrics.py <label>=<data dir> ..."""
import glob, json, sys
import chess
sys.path.insert(0, str(Path(__file__).resolve().parents[2])); import fow
from referee import FowBoard, observation
V = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
print(f"{'config':12s} {'games':>5s} {'score':>6s} {'losses':>6s} {'king lost to unseen':>19s} {'mat lost/game':>13s} {'to unseen/game':>14s} {'king moves/game':>15s} {'fog-walk/game':>13s}")
for arg in sys.argv[1:]:
    label, d = arg.split("=")
    n = wins = draws = losses = kl_unseen = 0; mat = mat_unseen = kmoves = fogwalk = 0.0
    for f in sorted(glob.glob(d + "/*.json")):
        g = json.load(open(f))
        us = chess.WHITE if g["white"] != "obscuro_v3" else chess.BLACK
        r = g["result"]; n += 1
        if r == "1/2-1/2": draws += 1
        elif (r == "1-0") == (us == chess.WHITE): wins += 1
        else: losses += 1
        b = FowBoard()
        frames = g["frames"]
        for i, fr in enumerate(frames[1:]):
            mv = chess.Move.from_uci(fr["move"]); mover = b.turn
            obs = observation(b, us)
            victim = b.piece_at(mv.to_square)
            if mover == us:
                if b.piece_at(mv.from_square).piece_type == chess.KING: kmoves += 1
                after = b.copy(stack=False); after.push(mv)
                if any(obs[a] == "?" for a in after.attackers(not us, mv.to_square)): fogwalk += 1
                if i == len(frames) - 2 and r != "1/2-1/2":   # our last move lost the game: who attacks the king?
                    k = after.king(us)
                    if k is not None and any(obs[a] == "?" for a in after.attackers(not us, k)): kl_unseen += 1
            elif victim is not None and victim.piece_type != chess.KING:
                mat += V[victim.piece_type]
                if obs[mv.from_square] == "?": mat_unseen += V[victim.piece_type]
            b.push(mv)
    if n:
        print(f"{label:12s} {n:5d} {(wins + 0.5 * draws) / n:6.3f} {losses:6d} {kl_unseen:19d} {mat / n:13.2f} {mat_unseen / n:14.2f} {kmoves / n:15.2f} {fogwalk / n:13.2f}")
