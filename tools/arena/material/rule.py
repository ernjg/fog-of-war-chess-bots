"""View-computable exposure with an empirical prior, calibration us vs GG, and the cost/benefit of a threshold rule.
E(s) = sum over unseen squares u that could attack s (ray through seen-empty/unseen squares; knight/pawn geometry)
       of p(u) * share(kind), p(u) = empirical P(enemy piece on an unseen square | rank distance from enemy back rank),
       share(kind) = unaccounted enemy pieces of that kind / unaccounted total (bot knows its captures and what it sees)."""
import pickle, sys
from collections import Counter, defaultdict
R = "/Users/ernestogomez/Desktop/fog-of-war-chess-bots"
sys.path.insert(0, R); sys.path.insert(0, R + "/starter")
import chess
from referee import FowBoard, fow_moves
sys.path.insert(0, "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/research/material")
from unseen_losses import captured_square, bal, VAL, SYM, US, GG, SP, OUT, INIT
def mean(xs): return sum(xs) / len(xs) if xs else float("nan")

def games():
    ours = pickle.load(open(SP + "replays_cache.pkl", "rb")); gg = pickle.load(open(SP + "gg_games.pkl", "rb"))
    for gid, g in ours.items():
        us = chess.WHITE if g["whitePlayerId"] == US else chess.BLACK
        if (g["whiteVersion"] if us else g["blackVersion"]) != 4: continue
        yield "us", gid, g["frames"], us
    for gid, g in gg.items():
        m = g["meta"]; us = chess.WHITE if m["whitePlayerId"] == GG else chess.BLACK
        yield "gg", gid, g["rep"]["frames"], us

def replay(frames):
    b = FowBoard(); hist = []
    for f in frames[1:]:
        mv = chess.Move.from_uci(f["move"]); hist.append((b.copy(stack=False), mv, b.turn, f)); b.push(mv)
    return hist, b

def rel_rank(sq, opp):
    r = chess.square_rank(sq)
    return r if opp == chess.BLACK else 7 - r   # 7 = enemy back rank ... 0 = our back rank  (as distance from our side)

# pass 1: prior p(enemy piece | unseen square, rel rank, phase)
def prior():
    cnt = Counter(); hit = Counter()
    for who, gid, frames, us in games():
        hist, _ = replay(frames)
        for i, (P, mv, mover, f) in enumerate(hist):
            if mover != us: continue
            V = frames[i]["white" if us else "black"]; ph = min(i // 20, 3)
            for s in range(64):
                if V[s] != "?": continue
                k = (rel_rank(s, not us), ph); cnt[k] += 1
                p = P.piece_at(s)
                if p is not None and p.color != us and p.piece_type != chess.KING: hit[k] += 1
    return {k: hit[k] / cnt[k] for k in cnt}

def exposure(P, us, V, s, pri, ph):
    opp = not us
    vis = Counter()
    for sq in range(64):
        ch = V[sq]
        if ch not in "?-" and (ch.isupper() == (opp == chess.WHITE)): vis[chess.Piece.from_symbol(ch).piece_type] += 1
    alive = Counter(p.piece_type for p in P.piece_map().values() if p.color == opp)
    unacc = {pt: max(0, alive[pt] - vis[pt]) for pt in INIT if pt != chess.KING}
    tot = sum(unacc.values())
    if tot == 0: return 0.0
    share = {pt: unacc[pt] / tot for pt in unacc}
    E = 0.0
    f, r = chess.square_file(s), chess.square_rank(s)
    def pu(sq): return pri.get((rel_rank(sq, opp), ph), 0.0)
    if share[chess.KNIGHT] > 0:
        for df, dr in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)):
            ff, rr = f + df, r + dr
            if 0 <= ff < 8 and 0 <= rr < 8 and V[chess.square(ff, rr)] == "?": E += pu(chess.square(ff, rr)) * share[chess.KNIGHT]
    if share[chess.PAWN] > 0:
        rr = r - 1 if opp == chess.WHITE else r + 1
        for ff in (f - 1, f + 1):
            if 0 <= ff < 8 and 0 <= rr < 8 and V[chess.square(ff, rr)] == "?": E += pu(chess.square(ff, rr)) * share[chess.PAWN]
    for dirs, kinds in ((((1, 0), (-1, 0), (0, 1), (0, -1)), (chess.ROOK, chess.QUEEN)), (((1, 1), (1, -1), (-1, 1), (-1, -1)), (chess.BISHOP, chess.QUEEN))):
        k = sum(share[kd] for kd in kinds)
        if k == 0: continue
        for df, dr in dirs:
            ff, rr = f + df, r + dr; passed = 1.0
            while 0 <= ff < 8 and 0 <= rr < 8:
                sq = chess.square(ff, rr); ch = V[sq]
                if ch == "?":
                    E += passed * pu(sq) * k; passed *= (1 - pu(sq))   # a hidden piece there blocks the ray behind it
                elif ch != "-": break
                ff += df; rr += dr
    return E

def loss_after(P, us, V, pri, ph):
    """Expected free loss (points) after a move, view-only: sum over own undefended non-king pieces of E(s)*value,
    plus for defended pieces E(s)*max(0, value-3) (a hidden minor can still win the exchange)."""
    tot = 0.0; parts = []
    for s, p in P.piece_map().items():
        if p.color != us or p.piece_type == chess.KING: continue
        e = exposure(P, us, V, s, pri, ph)
        v = VAL[p.piece_type]
        l = e * (v if not P.is_attacked_by(us, s) else max(0, v - 3))
        tot += l; parts.append((s, e, l))
    return tot, parts

def main():
    pri = prior()
    print("prior P(enemy piece | unseen square) by (rank distance from our side 0..7, phase):")
    for ph in range(4): print(" phase", ph, [round(pri.get((rk, ph), 0), 3) for rk in range(8)])
    rows = {"us": [], "gg": []}; ng = Counter()
    for who, gid, frames, us in games():
        ng[who] += 1
        hist, final = replay(frames); pos = lambda k: hist[k][0] if k < len(hist) else final
        for i, (P, mv, mover, f) in enumerate(hist):
            if mover != us: continue
            V = frames[i]["white" if us else "black"]; ph = min(i // 20, 3)
            after = P.copy(stack=False); after.push(mv)
            iscap = P.is_capture(mv); capval = VAL[P.piece_at(captured_square(P, mv)).piece_type] if iscap else 0
            L, parts = loss_after(after, us, V, pri, ph)
            nxt = hist[i + 1] if i + 1 < len(hist) else None
            lost = 0; lost_sq = None
            if nxt is not None and nxt[0].is_capture(nxt[1]) and frames[i + 1]["white" if us else "black"][nxt[1].from_square] == "?":
                lost_sq = captured_square(nxt[0], nxt[1]); lost = VAL[nxt[0].piece_at(lost_sq).piece_type]
            gain = bal(pos(i + 3), us) - bal(P, us)
            mp = P.piece_at(mv.from_square).piece_type
            dest_e = next((e for s, e, l in parts if s == mv.to_square), 0.0)
            dest_def = after.is_attacked_by(us, mv.to_square)
            # alternatives: min expected loss over legal moves (view-only), and the count below a threshold
            alts = []
            for m in fow_moves(P):
                if m == chess.Move.null() or m == mv: continue
                Q = P.copy(stack=False); Q.push(m)
                alts.append((loss_after(Q, us, V, pri, ph)[0], m))
            minalt = min((a for a, _ in alts), default=None)
            rows[who].append(dict(game=gid, ply=i + 1, pt=SYM[mp], cap=iscap, capval=capval, L=L, dest_e=dest_e, dest_def=dest_def,
                                  val=VAL[mp], lost=lost, lost_is_dest=(lost_sq == mv.to_square), gain=gain, minalt=minalt,
                                  n_alt_below=sum(1 for a, _ in alts if a <= 0.5 * L) if L > 0 else None, king=mp == chess.KING))
        print(who, gid, len(rows[who]), flush=True, file=sys.stderr)
    pickle.dump((rows, ng, pri), open(OUT + "rule_rows.pkl", "wb"))

if __name__ == "__main__":
    main()
