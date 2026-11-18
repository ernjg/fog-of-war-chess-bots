"""Is the belief calibrated about threats? Replay every arena game through eBotI's belief
(opponent model on). At each of our decisions, for the move we played, record per sampled
board: weight, how many of our pieces an UNSEEN enemy piece attacks after the move, whether
the moved piece's square is attacked by an unseen piece, whether our king is. Record the
truth too. Offline: fit a per-threat board weight so predicted rates match realized ones.
Usage: python belief_calibration.py <first game index> <last game index>"""
import json, os, pickle, random, sys, time
import numpy as np
R = str(Path(__file__).resolve().parents[2])
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
lo, hi = int(sys.argv[1]), int(sys.argv[2])
pool = EnginePool.start([SF], 2, time.monotonic() + 8, cwd=SF.rsplit("/", 1)[0])

def threats(board, us, obs_before, moved_to):
    """(pieces of ours attacked by an unseen enemy piece, moved piece attacked?, king attacked?)"""
    count = 0; dest = 0; king = 0
    for sq, piece in board.piece_map().items():
        if piece.color != us: continue
        hit = any(obs_before[a] == "?" for a in board.attackers(not us, sq))
        if hit:
            count += 1
            if sq == moved_to: dest = 1
            if piece.piece_type == chess.KING: king = 1
    return count, dest, king

out = []
ids = [gid for gid in cache if gid in games][lo:hi]
for n, gid in enumerate(ids):
    g = games[gid]; rep = cache[gid]
    us = chess.WHITE if g["whitePlayerId"] == team else chess.BLACK
    if (g["whiteVersion"] if us else g["blackVersion"]) != 4: continue
    policy = opp.OpponentPolicy(pool, seconds=0.3)
    ps = PositionSet(us, [HELPER], 200000, random.Random(0))
    board = FowBoard(); ps.observe(rep["frames"][0]["white" if us else "black"])
    for f in rep["frames"][1:]:
        mv = chess.Move.from_uci(f["move"]); mover = board.turn
        if mover == us and not ps.failure and len(ps) > 0 and ps.states:
            obs = observation(board, us)
            weights = np.asarray(ps.weights if ps.weighted else [1.0] * len(ps.states), float)
            rows = []
            for st in ps.states:
                if mv not in st.pseudo_legal_moves and not st.is_legal(mv):
                    rows.append((0, 0, 0, 0, 0)); continue
                k0 = threats(st, us, obs, -1)[2]     # king attacked from the fog BEFORE our move (a phantom check?)
                b2 = st.copy(stack=False); b2.push(mv)
                c, d, k = threats(b2, us, obs, mv.to_square)
                rows.append((1, c, d, k, k0))
            arr = np.asarray(rows, dtype=np.int16)
            truth = board.copy(stack=False); truth.push(mv)
            tc, td, tk = threats(truth, us, obs, mv.to_square)
            tk0 = threats(board, us, obs, -1)[2]
            # did the opponent actually capture the moved piece / attack the king next move? (realized)
            out.append(dict(game=gid, ply=len(out), size=len(ps), weights=weights.astype(np.float32), rows=arr,
                            truth=(tc, td, tk, tk0), pieces=len([1 for _, p in board.piece_map().items() if p.color == us]),
                            king_move=board.piece_at(mv.from_square).piece_type == chess.KING, moved=chess.piece_name(board.piece_at(mv.from_square).piece_type)))
        board.push(mv)
        ps.observe(f["white" if us else "black"], own_move=mv if mover == us else None, policy=None if mover == us else policy)
        if ps.failure: break
    ps.close()
    print(f"{n+1}/{len(ids)} {gid[:8]} decisions so far {len(out)}", flush=True)
pickle.dump(out, open(S + f"/calib_{lo}_{hi}.pkl", "wb"))
pool.close()
print("DONE")
