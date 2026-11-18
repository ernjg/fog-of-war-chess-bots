"""Replay our arena games through eBotI's position set (same as v4). At each of our decisions
ask the helper whether the TRUE board is in the set and with what weight share. Record set
size, exactness, repairs, and whether our move walked into an unseen attack on the true board.
Usage: python truth_in_set.py <lo> <hi> [all|losses]"""
import json, os, pickle, random, sys, time
from pathlib import Path
R = "/Users/ernestogomez/Desktop/fog-of-war-chess-bots"
sys.path.insert(0, R); sys.path.insert(0, R + "/bots/eBotI")
import chess, fow
from referee import FowBoard, observation
from eBotI.position_set import PositionSet
from eBotI.engine import EnginePool
from eBotI import opponent as opp
S = os.environ.get("ARENA_CACHE", str(Path(__file__).resolve().parents[2] / "data" / "arena"))
team = "e8915d7524054718ab675bc9ba14da0a"
HELPER = R + "/bots/eBotI/positions"; SF = R + "/bots/eBotI/stockfish/src/stockfish"
cache = pickle.load(open(S + "/replays_cache.pkl", "rb")); games = {g["id"]: g for g in json.load(open(S + "/games_list.json"))}
lo, hi = int(sys.argv[1]), int(sys.argv[2]); which = sys.argv[3] if len(sys.argv) > 3 else "losses"
pool = EnginePool.start([SF], 2, time.monotonic() + 8, cwd=SF.rsplit("/", 1)[0])

def unseen_king_attack(board, us, obs):
    k = board.king(us)
    return k is not None and any(obs[a] == "?" for a in board.attackers(not us, k))

out = []
ids = [gid for gid in cache if gid in games][lo:hi]
for n, gid in enumerate(ids):
    g = games[gid]; rep = cache[gid]
    us = chess.WHITE if g["whitePlayerId"] == team else chess.BLACK
    if (g["whiteVersion"] if us else g["blackVersion"]) != 4: continue
    lost = (g["result"] == "0-1") == us
    if which == "losses" and not lost: continue
    policy = opp.OpponentPolicy(pool, seconds=0.3)
    ps = PositionSet(us, [HELPER], 200000, random.Random(0))
    board = FowBoard(); ps.observe(rep["frames"][0]["white" if us else "black"])
    frames = rep["frames"]; last = len(frames) - 1
    for i, f in enumerate(frames[1:], 1):
        mv = chess.Move.from_uci(f["move"]); mover = board.turn
        if mover == us and not ps.failure:
            obs = observation(board, us)
            found, share, total = False, 0.0, 0.0
            try:
                for fen in {board.fen(en_passant="legal"), board.fen(en_passant="fen"), board.fen(en_passant="xfen")}:
                    hdr, _ = ps.helper.ask("find " + fen, time.monotonic() + 5)
                    w = hdr.split()
                    if w[0] == "found":
                        found = True; share = float(w[1]) / float(w[2]) if float(w[2]) > 0 else 0.0; break
            except Exception as e:
                found = None
            after = board.copy(stack=False); after.push(mv)
            out.append(dict(game=gid, ply=i, last=(i == last), lost=lost, size=len(ps), exact=ps.exact, repairs=ps.repairs,
                            found=found, share=share, uniform=1.0 / max(len(ps), 1), ess=ps.effective_size(),
                            walk=unseen_king_attack(after, us, obs), check0=unseen_king_attack(board, us, obs),
                            king_move=board.piece_at(mv.from_square).piece_type == chess.KING,
                            pieces=len([1 for _, p in board.piece_map().items() if p.color == us]),
                            unseen=sum(1 for s in range(64) if obs[s] == "?")))
        board.push(mv)
        ps.observe(f["white" if us else "black"], own_move=mv if mover == us else None, policy=None if mover == us else policy)
        if ps.failure:
            out.append(dict(game=gid, ply=i, failure=ps.failure)); break
    ps.close()
    print(f"{n+1}/{len(ids)} {gid[:8]} lost={lost} decisions {len(out)}", flush=True)
pickle.dump(out, open(S + f"/truth_{which}_{lo}_{hi}.pkl", "wb"))
pool.close()
print("DONE")
