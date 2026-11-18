"""Same evidence, different aggregation. Replay arena games through eBotI's belief; at each
of our decisions gather Stockfish evidence ONCE, then choose a move under several
(attacked_weight, threat_weight) settings and judge every choice on the true board.
Usage: python paired_aggregation.py <first game> <last game> <budget s>"""
import json, os, pickle, random, sys, time
import numpy as np
R = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, R); sys.path.insert(0, R + "/bots/eBotI")
import chess, fow
from referee import FowBoard, observation, fow_moves
from uniform_random import candidates
from eBotI.position_set import PositionSet
from eBotI.engine import EnginePool, Job
from eBotI import opponent as opp
from eBotI import stockfish_search as ss
from eBotI.stockfish_search import Evidence
S = os.environ.get("ARENA_CACHE", str(Path(__file__).resolve().parents[2] / "data" / "arena"))
team = "e8915d7524054718ab675bc9ba14da0a"
HELPER = R + "/bots/eBotI/positions"; SF = R + "/bots/eBotI/stockfish/src/stockfish"
cache = pickle.load(open(S + "/replays_cache.pkl", "rb")); games = {g["id"]: g for g in json.load(open(S + "/games_list.json"))}
lo, hi, budget = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
pool = EnginePool.start([SF], 4, time.monotonic() + 8, cwd=SF.rsplit("/", 1)[0])
ss.MAX_ROOTS, ss.CVAR_WEIGHT = 64, 0.0
SETTINGS = [(6.0, 1.0), (2.5, 1.0), (1.0, 1.0), (6.0, 1.5), (2.5, 1.5)]

def wins(b):
    k = b.king(not b.turn); return k is None or b.is_attacked_by(b.turn, k)

def fog_threats(board, us, obs):
    """our pieces attacked by an enemy piece standing on a square we cannot see"""
    n = 0
    for sq, piece in board.piece_map().items():
        if piece.color == us and any(obs[a] == "?" for a in board.attackers(not us, sq)): n += 1
    return n

def true_values(board, side, moves):
    jobs, out = [], []
    for m in moves:
        b2 = board.copy(stack=False); b2.push(m)
        if wins(b2): out.append(-1.0); jobs.append(None); continue
        if b2.king(True) is None or b2.king(False) is None: out.append(None); jobs.append(None); continue
        out.append(b2); jobs.append(Job(b2.fen(), 8))
    real = [j for j in jobs if j is not None]
    res = iter(pool.run(real, time.monotonic() + 25.0, 0.02, 1.0) if real else [])
    vals = []
    for j, o in zip(jobs, out):
        if j is None: vals.append(o); continue
        r = next(res); v = r.best() if r is not None else None
        vals.append(None if v is None else (v if o.turn == side else -v))
    return vals

def exact_risk(ps, moves):
    ucis = " ".join(m.uci() for m in moves)
    _, rows = ps.helper.ask(f"risk 0 600 0 {len(moves)} {ucis}", time.monotonic() + 10)
    risk = {r.split()[1]: float(r.split()[2]) for r in rows}
    _, rows = ps.helper.ask(f"trap 4000 600 0 {len(moves)} {ucis}", time.monotonic() + 30)
    trap = {r.split()[1]: float(r.split()[2]) for r in rows}
    return np.array([risk[m.uci()] + (1 - risk[m.uci()]) * trap[m.uci()] for m in moves])

records = []
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
        if mover == us and not ps.failure and len(ps) > 1 and ps.states:
            obs = observation(board, us)
            rights = board.castling_rights & (chess.BB_RANK_1 if us else chess.BB_RANK_8)
            moves = candidates(obs, us, rights)[1]
            weights = ps.weights if ps.weighted else None
            ev = ss.gather(pool, ps.states, moves, us, time.monotonic() + budget, random.Random(1), weights)
            if ev is not None and ev.scan_states is not None:
                risk_exact = exact_risk(ps, moves)
                threats = np.array([fog_threats(st, us, obs) for st in ev.scan_states], float)
                base_scan = ev.scan_count if ev.scan_count is not None else np.ones(len(ev.scan_states))
                tv = true_values(board, us, moves)
                known = [v for v in tv if v is not None]; best = max(known) if known else None
                rec = dict(game=gid, played=mv.uci(), size=len(ps), pieces=len([1 for p in board.piece_map().values() if p.color == us]),
                           in_fog_check=any(obs[a] == "?" for a in board.attackers(not us, board.king(us))), choices={},
                           moves=[m.uci() for m in moves], true_values=tv, exact_risk=risk_exact, threats=threats,
                           king_moves=[board.piece_at(m.from_square).piece_type == chess.KING for m in moves],
                           fog_after=[fog_threats((lambda b: (b.push(m), b)[1])(board.copy(stack=False)), us, obs) for m in moves],
                           fog_before=fog_threats(board, us, obs),
                           ev=dict(scan_attacked=ev.scan_attacked, scan_suicide=ev.scan_suicide, root_attacked=ev.root_attacked,
                                   root_suicide=ev.root_suicide, root_values=ev.root_values, scan_count=base_scan, root_index=ev.root_index))
                for aw, tw in SETTINGS:
                    scale = tw ** threats
                    ev2 = Evidence(ev.scan_attacked, ev.scan_suicide, ev.root_attacked, ev.root_suicide, ev.root_values, ev.sampled, ev.depths,
                                   base_scan * scale, (base_scan * scale)[ev.root_index])
                    value, risk = ss.weigh(ev2, attacked_weight=aw, exact_risk=risk_exact)
                    top = int(np.argmax(value + 1e-9 * np.arange(len(moves))))
                    m = moves[top]; after = board.copy(stack=False); after.push(m)
                    rec["choices"][(aw, tw)] = dict(move=m.uci(), king_lost=wins(after), king_move=board.piece_at(m.from_square).piece_type == chess.KING,
                                                    fog_attacked=fog_threats(after, us, obs) > fog_threats(board, us, obs),
                                                    value_lost=None if best is None or tv[top] is None else max(0.0, best - tv[top]))
                records.append(rec)
        board.push(mv)
        ps.observe(f["white" if us else "black"], own_move=mv if mover == us else None, policy=None if mover == us else policy)
        if ps.failure: break
    ps.close()
    print(f"{n+1}/{len(ids)} {gid[:8]} decisions {len(records)}", flush=True)
    pickle.dump(records, open(S + f"/paired2_{lo}_{hi}.pkl", "wb"))
pool.close(); print("DONE")
