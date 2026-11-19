"""Where do points lost to unseen captures come from? Per-capture rows for us (v4) and Greek Gift (as victim),
plus per-decision hazard rows for every move of the victim side. Pure replay, no engine.
Usage: uv run python unseen_losses.py   (from repo root)"""
import pickle, sys, os
from collections import Counter, defaultdict
R = "/Users/ernestogomez/Desktop/fog-of-war-chess-bots"
sys.path.insert(0, R); sys.path.insert(0, R + "/starter")
import chess
from referee import FowBoard, fow_moves
SP = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/"
OUT = SP + "research/material/"
US = "e8915d7524054718ab675bc9ba14da0a"; GG = "f394d843d970454f868c38c7f6963cc9"
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
SYM = {chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B", chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}
INIT = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1, chess.KING: 1}

def material(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)

def bal(b, us):
    return material(b, us) - material(b, not us)

def captured_square(b, mv):
    if b.is_en_passant(mv):
        return mv.to_square - 8 if b.turn == chess.WHITE else mv.to_square + 8
    return mv.to_square

def exposure_loss(P, us, view):
    """True-board hazard after a move of ours: for each of our pieces attacked by an enemy piece whose square is
    unseen in `view` (our view at the decision), the material we stand to lose: undefended -> value; defended ->
    max(0, value - cheapest unseen attacker). Returns (total, max_single, n_pieces)."""
    tot = 0; mx = 0; n = 0
    for s, p in P.piece_map().items():
        if p.color != us or p.piece_type == chess.KING:
            continue
        att = [a for a in P.attackers(not us, s) if view[a] == "?"]
        if not att:
            continue
        v = VAL[p.piece_type]
        if P.is_attacked_by(us, s):
            loss = max(0, v - min(VAL[P.piece_at(a).piece_type] for a in att))
        else:
            loss = v
        if loss > 0:
            n += 1; tot += loss; mx = max(mx, loss)
    return tot, mx, n

def fog_lines(P, us, view, s):
    """View-computable exposure of square s: number of (unseen square, piece kind) pairs from which an UNACCOUNTED
    enemy piece could attack s. Rays stop at seen occupied squares, pass through seen-empty and unseen squares.
    Unaccounted = initial count - captured by us - visible enemy pieces of that kind."""
    opp = not us
    # enemy pieces visible to us
    vis = Counter()
    for sq in range(64):
        ch = view[sq]
        if ch not in "?-" and (ch.isupper() == (opp == chess.WHITE)):
            vis[chess.Piece.from_symbol(ch).piece_type] += 1
    alive = Counter({pt: sum(1 for p in P.piece_map().values() if p.color == opp and p.piece_type == pt) for pt in INIT})
    # alive is true-board count; the bot knows it too: initial minus what it captured (captures are observed)
    unacc = {pt: alive[pt] - vis[pt] for pt in INIT}
    n = 0
    f, r = chess.square_file(s), chess.square_rank(s)
    # knights
    if unacc[chess.KNIGHT] > 0:
        for df, dr in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)):
            ff, rr = f + df, r + dr
            if 0 <= ff < 8 and 0 <= rr < 8 and view[chess.square(ff, rr)] == "?":
                n += 1
    # pawns (enemy pawn attacks s from the enemy's side)
    if unacc[chess.PAWN] > 0:
        rr = r + (1 if opp == chess.WHITE else -1) * -1  # white pawn attacks upward: pawn sits one rank below s
        rr = r - 1 if opp == chess.WHITE else r + 1
        for ff in (f - 1, f + 1):
            if 0 <= ff < 8 and 0 <= rr < 8 and view[chess.square(ff, rr)] == "?":
                n += 1
    # sliders
    for dirs, kinds in ((((1, 0), (-1, 0), (0, 1), (0, -1)), (chess.ROOK, chess.QUEEN)),
                        (((1, 1), (1, -1), (-1, 1), (-1, -1)), (chess.BISHOP, chess.QUEEN))):
        k = sum(1 for kd in kinds if unacc[kd] > 0)
        if k == 0:
            continue
        for df, dr in dirs:
            ff, rr = f + df, r + dr
            while 0 <= ff < 8 and 0 <= rr < 8:
                sq = chess.square(ff, rr)
                ch = view[sq]
                if ch == "?":
                    n += k
                elif ch != "-":
                    break
                ff += df; rr += dr
    return n

def analyze(frames, us):
    b = FowBoard(); hist = []
    for f in frames[1:]:
        mv = chess.Move.from_uci(f["move"]); hist.append((b.copy(stack=False), mv, b.turn, f)); b.push(mv)
    final = b
    def pos(k):
        return hist[k][0] if k < len(hist) else final
    def view(k, c):
        return frames[k]["white" if c == chess.WHITE else "black"]
    opp = not us
    caps = []; decs = []
    for i, (P1, mv, mover, f) in enumerate(hist):
        if mover == us:
            # per-decision hazard row
            V = view(i, us)
            after = P1.copy(stack=False); after.push(mv)
            tot, mx, n = exposure_loss(after, us, V)
            moved_pt = P1.piece_at(mv.from_square).piece_type
            dest = mv.to_square
            att_unseen = [a for a in after.attackers(opp, dest) if V[a] == "?"]
            defended = after.is_attacked_by(us, dest)
            iscap = P1.is_capture(mv)
            capval = VAL[P1.piece_at(captured_square(P1, mv)).piece_type] if iscap else 0
            # what happened next: was the moved piece taken by an unseen attacker on the very next ply?
            taken = None
            if i + 1 < len(hist):
                nmv = hist[i + 1][1]
                if hist[i + 1][0].is_capture(nmv) and captured_square(hist[i + 1][0], nmv) == dest:
                    taken = "unseen" if view(i + 1, us)[nmv.from_square] == "?" else "seen"
            net2 = bal(pos(i + 3), us) - bal(P1, us)   # our move, their reply, our reply  (relative to before our move)
            net2_after = bal(pos(i + 3), us) - bal(after, us)
            decs.append(dict(ply=i + 1, pt=SYM[moved_pt], dest=chess.square_name(dest), cap=iscap, capval=capval,
                             dest_unseen_att=len(att_unseen), dest_unseen_min=min((VAL[after.piece_at(a).piece_type] for a in att_unseen), default=None),
                             defended=defended, haz_tot=tot, haz_max=mx, haz_n=n, taken=taken, net2=net2, net2_after=net2_after,
                             lines=fog_lines(after, us, V, dest) if moved_pt != chess.KING else -1, king=moved_pt == chess.KING,
                             pre_haz=exposure_loss(P1, us, V)[0]))
            continue
        # opponent move: capture of our piece by an attacker we could not see
        if not P1.is_capture(mv):
            continue
        T = captured_square(P1, mv); A = mv.from_square
        Vus = view(i, us)   # our view before the opponent's move (= after our move)
        if Vus[A] != "?":
            continue
        cp = P1.piece_at(T); val = VAL[cp.piece_type]
        row = dict(ply=i + 1, pt=SYM[cp.pt] if False else SYM[cp.piece_type], val=val, by=SYM[P1.piece_at(A).piece_type],
                   T=chess.square_name(T), A=chess.square_name(A))
        # (a) classification relative to our previous decision
        if i == 0:
            row["cat"] = "none"
        else:
            P0, omv, _, _ = hist[i - 1]; V0 = view(i - 1, us)
            was_there = (P0.piece_at(T) is not None and P0.piece_at(T).color == us and P0.piece_at(T).piece_type == cp.piece_type
                         and omv.from_square != T)
            if not was_there:
                row["cat"] = "moved_in"
                row["our_cap"] = P0.is_capture(omv)
                row["our_capval"] = VAL[P0.piece_at(captured_square(P0, omv)).piece_type] if row["our_cap"] else 0
            else:
                pa = P0.piece_at(A)
                if pa is not None and pa.color == opp and T in P0.attacks(A):
                    # how many plies the attacker already attacked T from A (positions before our move going back)
                    k = 0
                    for j in range(i - 1, -1, -1):
                        pb = hist[j][0]
                        if pb.piece_at(A) == pa and pb.piece_at(T) is not None and T in pb.attacks(A):
                            k += 1
                        else:
                            break
                    row["cat"] = "left_fresh" if k <= 1 else "left_standing"
                    row["standing_plies"] = k
                    row["saw_at_decision"] = V0[A] != "?"
                else:
                    row["cat"] = "opened"
            row["our_move"] = omv.uci(); row["our_pt"] = SYM[P0.piece_at(omv.from_square).piece_type]
            # counterfactual: alternatives at our decision with zero true-board hazard
            if row["cat"] in ("moved_in", "left_fresh", "left_standing", "opened"):
                cands = [m for m in fow_moves(P0) if m != chess.Move.null()]
                zero = 0; zero_noncap = 0; best = None
                for m in cands:
                    Q = P0.copy(stack=False); Q.push(m)
                    t, _, _ = exposure_loss(Q, us, V0)
                    if t == 0:
                        zero += 1
                        if not P0.is_capture(m): zero_noncap += 1
                    best = t if best is None else min(best, t)
                after = P0.copy(stack=False); after.push(omv)
                row["chosen_haz"] = exposure_loss(after, us, V0)[0]; row["pre_haz"] = exposure_loss(P0, us, V0)[0]
                row["n_alt"] = len(cands); row["zero_alt"] = zero; row["zero_alt_noncap"] = zero_noncap; row["min_alt_haz"] = best
                row["lines"] = fog_lines(after, us, V0, T)
        # (b) defended / exchange
        row["defended"] = P1.is_attacked_by(us, T)
        row["n_def"] = len(P1.attackers(us, T))
        row["by_val"] = VAL[P1.piece_at(A).piece_type]
        b0 = bal(P1, us)
        row["net2"] = bal(pos(i + 3), us) - b0          # capture + our reply + their reply
        row["net1"] = bal(pos(i + 2), us) - b0          # capture + our reply
        # (c) running balance
        row["bal_before"] = b0; row["bal_10"] = bal(pos(i + 11), us)
        row["plies_left"] = len(hist) - i
        caps.append(row)
    return caps, decs, len(hist)

def run():
    ours = pickle.load(open(SP + "replays_cache.pkl", "rb"))
    gg = pickle.load(open(SP + "gg_games.pkl", "rb"))
    res = {"us": [], "gg": []}
    for gid, g in ours.items():
        us = chess.WHITE if g["whitePlayerId"] == US else chess.BLACK
        if (g["whiteVersion"] if us else g["blackVersion"]) != 4:
            continue
        r = g["result"]
        out = "draw" if r == "1/2-1/2" else ("win" if (r == "1-0") == us else "loss")
        caps, decs, n = analyze(g["frames"], us)
        res["us"].append(dict(id=gid, outcome=out, plies=n, caps=caps, decs=decs, opp=g["black"] if us else g["white"]))
    for gid, g in gg.items():
        m = g["meta"]; us = chess.WHITE if m["whitePlayerId"] == GG else chess.BLACK
        r = m["result"]
        out = "draw" if r == "1/2-1/2" else ("win" if (r == "1-0") == us else "loss")
        caps, decs, n = analyze(g["rep"]["frames"], us)
        res["gg"].append(dict(id=gid, outcome=out, plies=n, caps=caps, decs=decs, opp=m["black"] if us else m["white"]))
    pickle.dump(res, open(OUT + "rows.pkl", "wb"))
    for k in res:
        print(k, len(res[k]), Counter(g["outcome"] for g in res[k]), "unseen caps", sum(len(g["caps"]) for g in res[k]),
              "pts/game %.2f" % (sum(c["val"] for g in res[k] for c in g["caps"]) / len(res[k])))

if __name__ == "__main__":
    run()
