"""Which opponent model predicts arena opponents' moves better: Stockfish 1-ply on the true
board (v4) or Stockfish 1-ply on what the opponent can see (our unseen pieces removed)?
Replays the TRUE boards of our cached arena games; for every opponent move reports the
log-likelihood, rank and top-1 rate of the move played under each model.
Usage: python opp_model_calib.py <lo> <hi>"""
import json, math, os, pickle, sys, time
from pathlib import Path
R = "/Users/ernestogomez/Desktop/fog-of-war-chess-bots"
sys.path.insert(0, R); sys.path.insert(0, R + "/bots/eBotI")
import chess, fow
from referee import FowBoard, observation, fow_moves
from eBotI.engine import EnginePool, Job
from eBotI.opponent import move_odds, OTHER
from eBotI.stockfish_search import engine_accepts, engine_fen
S = os.environ.get("ARENA_CACHE", str(Path(__file__).resolve().parents[2] / "data" / "arena"))
team = "e8915d7524054718ab675bc9ba14da0a"
SF = R + "/bots/eBotI/stockfish/src/stockfish"
cache = pickle.load(open(S + "/replays_cache.pkl", "rb")); games = {g["id"]: g for g in json.load(open(S + "/games_list.json"))}
lo, hi = int(sys.argv[1]), int(sys.argv[2])
pool = EnginePool.start([SF], 2, time.monotonic() + 8, cwd=SF.rsplit("/", 1)[0])

def blind_board(board, opp):
    """The board as the opponent sees it: our pieces it cannot see are removed (our king stays)."""
    obs = observation(board, opp)
    vb = board.copy(stack=False)
    for sq, pc in list(board.piece_map().items()):
        if pc.color != opp and obs[sq] == "?" and pc.piece_type != chess.KING:
            vb.remove_piece_at(sq)
    return vb

def values_of(board):
    if not engine_accepts(board): return None
    res = pool.run([Job(engine_fen(board), 1)], time.monotonic() + 2.0, 2.0, 2.0)[0]
    if res is None or res.no_moves: return None
    d = res.complete_depth(list(res.scores))
    if d is None: return None
    return {m: f[d] for m, f in res.scores.items()}

rows = []
ids = [gid for gid in cache if gid in games][lo:hi]
for n, gid in enumerate(ids):
    g = games[gid]; rep = cache[gid]
    us = chess.WHITE if g["whitePlayerId"] == team else chess.BLACK
    if (g["whiteVersion"] if us else g["blackVersion"]) != 4: continue
    board = FowBoard()
    for i, f in enumerate(rep["frames"][1:], 1):
        mv = chess.Move.from_uci(f["move"]); mover = board.turn
        if mover != us:
            legal = [m.uci() for m in fow_moves(board)]
            n_moves = len(legal)
            row = dict(game=gid, ply=i, n=n_moves, move=mv.uci(), unseen_ours=0)
            obs = observation(board, mover)
            row["unseen_ours"] = sum(1 for sq, pc in board.piece_map().items() if pc.color == us and obs[sq] == "?")
            row["captures_unseen"] = bool(board.piece_at(mv.to_square)) and obs[mv.to_square] == "?"  # cannot happen by rule; kept as a check
            row["capture"] = bool(board.piece_at(mv.to_square))
            for label, b in (("true", board), ("blind", blind_board(board, mover))):
                vals = values_of(b)
                if vals is None: row[label] = None; continue
                vals = {m: v for m, v in vals.items() if m in legal}   # moves the view allows but the board does not: dropped
                row[label] = vals
            rows.append(row)
        board.push(mv)
    print(f"{n+1}/{len(ids)} {gid[:8]} rows {len(rows)}", flush=True)
pickle.dump(rows, open(S + f"/oppcal_{lo}_{hi}.pkl", "wb"))
pool.close(); print("DONE")
