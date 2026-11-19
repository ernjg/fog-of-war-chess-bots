"""Per-version behaviour metrics for Greek Gift from arena replays (see versions.md)."""
import json, os, pickle, sys, statistics as st
from collections import Counter, defaultdict
import numpy as np
R = "/Users/ernestogomez/Desktop/fog-of-war-chess-bots"
sys.path.insert(0, R); sys.path.insert(0, R + "/starter")
import chess
from referee import FowBoard, observation, fow_moves
SP = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/"
D = SP + "research/ggvers/"
G = "f394d843d970454f868c38c7f6963cc9"
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
VERS = [1, 2, 14, 16, 21, 25, 30]

def material(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)

def load():
    reps = {}
    for fn in os.listdir(D + "replays"):
        if fn.endswith(".json"):
            d = json.load(open(D + "replays/" + fn)); reps[d["id"]] = d
    for gid, g in pickle.load(open(SP + "gg_games.pkl", "rb")).items():
        reps[gid] = g["rep"]
    return reps

def analyze_game(rep):
    fr = rep["frames"]; inc = rep["timeControl"]["incrementSeconds"]
    me = chess.WHITE if rep["whitePlayerId"] == G else chess.BLACK
    r = rep["result"]
    outcome = "draw" if r == "1/2-1/2" else ("win" if (r == "1-0") == me else "loss")
    b = FowBoard()
    row = dict(me=me, outcome=outcome, reason=rep["reason"], plies=len(fr) - 1, color="W" if me else "B",
               moves=[], own_first=[], thinks=[], clock_at={}, caps_taken_unseen=0, caps_lost_unseen=0,
               caps_taken=0, caps_lost=0, king_moves=0, king_into_attack=0, walkins=0, quiet=0, quiet_unseen_att=0,
               quiet_unseen_enprise=0, hang_moves=0, king_into_attack_nf=0, walkins_nf=0, exposed=0, exposure=0, kexp_moves=0, decisions=0, bal40=None, bal_end=None, kill=None, promos=0, checks_given=0,
               opp_thinks=[])
    n_own = 0
    for i, f in enumerate(fr[1:]):
        mv = chess.Move.from_uci(f["move"]); mover = b.turn
        prev = fr[i]
        myview = prev["white" if mover else "black"]
        victimview = prev["black" if mover else "white"]
        cb, ca = prev["clocks"][0 if mover else 1], f["clocks"][0 if mover else 1]
        think = cb - ca + inc
        iscap = b.is_capture(mv)
        if iscap:
            cap_pt = chess.PAWN if b.is_en_passant(mv) else b.piece_at(mv.to_square).piece_type
            unseen = victimview[mv.from_square] == "?"
        if mover == me:
            n_own += 1
            row["decisions"] += 1
            row["thinks"].append((f["ply"], n_own, cb, think))
            if n_own <= 3:
                row["own_first"].append(mv.uci())
            pc = b.piece_at(mv.from_square)
            ksq_before = b.king(me)
            att_before = b.is_attacked_by(not me, ksq_before)
            after = b.copy(stack=False); after.push(mv)
            ksq_after = after.king(me)
            att_after = after.is_attacked_by(not me, ksq_after)
            if pc.piece_type == chess.KING:
                row["king_moves"] += 1
                if att_after:
                    row["king_into_attack"] += 1
                    if i < len(fr) - 2: row["king_into_attack_nf"] += 1
            if not att_before and att_after:
                row["walkins"] += 1
                if i < len(fr) - 2: row["walkins_nf"] += 1
            if iscap:
                row["caps_taken"] += VAL[cap_pt]
                if unseen:
                    row["caps_taken_unseen"] += VAL[cap_pt]
            if mv.promotion:
                row["promos"] += 1
            if after.is_attacked_by(me, after.king(not me)):
                row["checks_given"] += 1
            if not iscap and pc.piece_type != chess.KING:
                row["quiet"] += 1
                atts = [a for a in after.attackers(not me, mv.to_square) if myview[a] == "?"]
                if atts:
                    row["quiet_unseen_att"] += 1
                    defended = bool(after.attackers(me, mv.to_square))
                    moved_val = VAL[after.piece_at(mv.to_square).piece_type]
                    if (not defended) or min(VAL[after.piece_at(a).piece_type] for a in atts) < moved_val:
                        row["quiet_unseen_enprise"] += 1
            # king exposure: unseen squares (pre-move view) from which a queen/knight could hit the king on the true board after the move
            kk = after.king(me); ex = 0
            for s in chess.SQUARES:
                if myview[s] != "?" or s == kk:
                    continue
                if chess.BB_SQUARES[kk] & chess.BB_KNIGHT_ATTACKS[s]:
                    ex += 1
                elif (chess.BB_RAYS[s][kk]) and not (chess.between(s, kk) & after.occupied):
                    ex += 1
            row["exposure"] += ex
            if ex: row["exposed"] += 1
            # pieces left hanging to unseen attackers (any own non-king piece except the moved one)
            hang = False
            for sq, p in after.piece_map().items():
                if p.color != me or p.piece_type == chess.KING or sq == mv.to_square:
                    continue
                if after.attackers(me, sq):
                    continue
                if any(myview[a] == "?" for a in after.attackers(not me, sq)):
                    hang = True; break
            if hang:
                row["hang_moves"] += 1
        else:
            row["opp_thinks"].append(think)
            if iscap:
                row["caps_lost"] += VAL[cap_pt]
                if unseen:
                    row["caps_lost_unseen"] += VAL[cap_pt]
        b.push(mv)
        if f["ply"] in (40, 80):
            row["clock_at"][f["ply"]] = f["clocks"][0 if me else 1]
        if f["ply"] == 40:
            row["bal40"] = material(b, me) - material(b, not me)
    row["bal_end"] = material(b, me) - material(b, not me)
    row["clock_end"] = fr[-1]["clocks"][0 if me else 1]
    if rep["reason"] == "King capturable" and outcome == "loss":
        # fatal = our last move; was our king attacked before it?
        bb = FowBoard()
        for f in fr[1:-1]:
            bb.push(chess.Move.from_uci(f["move"]))
        assert bb.turn == me
        k = bb.king(me)
        row["kill"] = "check_unanswered" if bb.is_attacked_by(not me, k) else "walked_in"
    return row

def fit_time(thinks):
    """Grid fit think = a + (clock - r)/max(f, D - s*n) on own moves with clock > r+5, think >= 0.4. Returns params, median abs err."""
    T = np.array([(n, c, t) for ply, n, c, t in thinks if t >= 0.4])
    if len(T) < 50:
        return None
    n, c, t = T[:, 0], T[:, 1], T[:, 2]
    best = None
    for a in (0, 0.5, 1, 1.5, 2, 2.5, 3):
        for r in (0, 5, 10, 12, 15, 20, 30, 45, 60):
            m = c > r + 5
            if m.sum() < 50:
                continue
            for s in (0, 0.25, 0.5, 0.75, 1.0):
                for f in (4, 6, 8, 10, 15):
                    for Dd in np.arange(8, 80, 1.0):
                        pred = a + (c[m] - r) / np.maximum(f, Dd - s * n[m])
                        err = np.median(np.abs(pred - t[m]))
                        if best is None or err < best[0]:
                            best = (err, a, r, Dd, s, f, int(m.sum()))
    return best

def bucket(ply):
    return "1-10" if ply <= 10 else "11-20" if ply <= 20 else "21-40" if ply <= 40 else "41-60" if ply <= 60 else "61+"

def summarize(rows):
    S = {}
    n = len(rows); S["games"] = n
    S["W-D-L"] = "%d-%d-%d" % tuple(sum(1 for r in rows if r["outcome"] == o) for o in ("win", "draw", "loss"))
    S["score"] = (sum(1 for r in rows if r["outcome"] == "win") + 0.5 * sum(1 for r in rows if r["outcome"] == "draw")) / n
    S["as white"] = sum(1 for r in rows if r["color"] == "W")
    th = [x for r in rows for x in r["thinks"]]
    S["moves"] = len(th)
    by = defaultdict(list)
    for ply, nn, c, t in th:
        by[bucket(ply)].append(t)
    for k in ("1-10", "11-20", "21-40", "41-60", "61+"):
        S["think " + k] = (st.mean(by[k]), st.median(by[k]), len(by[k])) if by[k] else None
    S["think all mean"] = st.mean(t for _, _, _, t in th)
    S["think max"] = max(t for _, _, _, t in th)
    S["think < 0.4 s share"] = sum(1 for _, _, _, t in th if t < 0.4) / len(th)
    S["think < 1 s share"] = sum(1 for _, _, _, t in th if t < 1.0) / len(th)
    # book: consecutive fast own moves from move 1
    bl = []
    for r in rows:
        k = 0
        for ply, nn, c, t in r["thinks"]:
            if t < 0.4: k += 1
            else: break
        bl.append(k)
    S["book length (own moves) mean/median/max"] = (st.mean(bl), st.median(bl), max(bl))
    S["games starting with a fast move"] = sum(1 for k in bl if k > 0) / n
    fast_plies = [nn for r in rows for ply, nn, c, t in r["thinks"] if t < 0.4]
    S["fast moves: own-move index dist"] = Counter(min(nn, 20) for nn in fast_plies)
    for p in (40, 80):
        v = [r["clock_at"][p] for r in rows if p in r["clock_at"]]
        S["clock at ply %d mean/median (n)" % p] = (st.mean(v), st.median(v), len(v)) if v else None
    v = [r["clock_end"] for r in rows]
    S["clock at end mean/median"] = (st.mean(v), st.median(v))
    S["games ending < 20 s"] = sum(1 for x in v if x < 20) / n
    S["clock min"] = min(v)
    S["opp think mean"] = st.mean(x for r in rows for x in r["opp_thinks"])
    S["time fit"] = fit_time(th)
    # openings
    for col in ("W", "B"):
        c = Counter(" ".join(r["own_first"]) for r in rows if r["color"] == col and len(r["own_first"]) == 3)
        S["first 3 as " + col] = c.most_common(6)
        c1 = Counter(r["own_first"][0] for r in rows if r["color"] == col and r["own_first"])
        S["first move as " + col] = c1.most_common(5)
        S["n as " + col] = sum(1 for r in rows if r["color"] == col)
    w = [r for r in rows if r["color"] == "W" and r["own_first"]]
    S["1.d4 share"] = sum(1 for r in w if r["own_first"][0] == "d2d4") / len(w) if w else None
    # king
    dec = sum(r["decisions"] for r in rows); km = sum(r["king_moves"] for r in rows)
    S["king moves share"] = km / dec
    S["king into attacked sq per 100 king moves"] = 100 * sum(r["king_into_attack"] for r in rows) / km if km else None
    S["walk-ins per 1000 decisions"] = 1000 * sum(r["walkins"] for r in rows) / dec
    S["walk-ins nonfatal per 1000"] = 1000 * sum(r["walkins_nf"] for r in rows) / dec
    S["king into attack nonfatal per 100"] = 100 * sum(r["king_into_attack_nf"] for r in rows) / km if km else None
    bc = defaultdict(list)
    for ply, nn, c, t in th:
        bc[">120" if c > 120 else "60-120" if c > 60 else "30-60" if c > 30 else "<30"].append(t)
    S["think by clock"] = {k: st.mean(v) for k, v in bc.items()}
    S["king exposed to an unseen square, share of moves"] = sum(r["exposed"] for r in rows) / dec
    S["king exposure (unseen squares hitting king) mean per move"] = sum(r["exposure"] for r in rows) / dec
    for col in ("W", "B"):
        seqs = [" ".join(r["own_first"]) for r in rows if r["color"] == col and len(r["own_first"]) == 3]
        S["distinct first-3 per game as " + col] = len(set(seqs)) / len(seqs) if seqs else None
    S["think percentiles 10/25/50/75/90 (clock>120)"] = np.percentile([t for _, _, c, t in th if c > 120], [10, 25, 50, 75, 90]).round(2).tolist()
    S["walk-ins per game"] = sum(r["walkins"] for r in rows) / n
    S["losses by kind"] = Counter(r["kill"] for r in rows if r["kill"])
    S["loss reasons"] = Counter(r["reason"] for r in rows if r["outcome"] == "loss")
    S["draw reasons"] = Counter(r["reason"] for r in rows if r["outcome"] == "draw")
    S["checks given per game"] = sum(r["checks_given"] for r in rows) / n
    # material
    S["unseen capture pts taken/game"] = sum(r["caps_taken_unseen"] for r in rows) / n
    S["unseen capture pts lost/game"] = sum(r["caps_lost_unseen"] for r in rows) / n
    S["all capture pts taken/game"] = sum(r["caps_taken"] for r in rows) / n
    S["all capture pts lost/game"] = sum(r["caps_lost"] for r in rows) / n
    S["unseen share of own captures"] = sum(r["caps_taken_unseen"] for r in rows) / max(1, sum(r["caps_taken"] for r in rows))
    S["unseen share of opp captures"] = sum(r["caps_lost_unseen"] for r in rows) / max(1, sum(r["caps_lost"] for r in rows))
    q = sum(r["quiet"] for r in rows)
    S["quiet moves onto unseen-attacked sq share"] = sum(r["quiet_unseen_att"] for r in rows) / q
    S["quiet moves en prise to unseen attacker share"] = sum(r["quiet_unseen_enprise"] for r in rows) / q
    S["moves leaving a piece hanging to unseen attacker share"] = sum(r["hang_moves"] for r in rows) / dec
    S["promotions per game"] = sum(r["promos"] for r in rows) / n
    # outcomes
    for o in ("win", "loss"):
        v = [r["bal40"] for r in rows if r["outcome"] == o and r["bal40"] is not None]
        S["bal at ply 40 in %ss mean (n)" % o] = (st.mean(v), len(v)) if v else None
        v = [r["bal_end"] for r in rows if r["outcome"] == o]
        S["bal at end in %ss mean (n)" % o] = (st.mean(v), len(v)) if v else None
    v = [r["bal40"] for r in rows if r["bal40"] is not None]
    S["ahead at ply 40 share"] = sum(1 for x in v if x > 0) / len(v) if v else None
    S["game length mean/median"] = (st.mean(r["plies"] for r in rows), st.median(r["plies"] for r in rows))
    S["win length mean"] = st.mean([r["plies"] for r in rows if r["outcome"] == "win"] or [0])
    S["wins <= 20 plies"] = sum(1 for r in rows if r["outcome"] == "win" and r["plies"] <= 20)
    S["draw share"] = sum(1 for r in rows if r["outcome"] == "draw") / n
    return S

def pool(games):
    """Opponent-pool metrics from the full game list."""
    byv = defaultdict(list)
    for g in games:
        gw = g["whitePlayerId"] == G
        v = g["whiteVersion"] if gw else g["blackVersion"]
        opp = g["blackPlayerId"] if gw else g["whitePlayerId"]
        oppv = g["blackVersion"] if gw else g["whiteVersion"]
        staff = g["blackStaff"] if gw else g["whiteStaff"]
        r = g["result"]; sc = 0.5 if r == "1/2-1/2" else (1.0 if (r == "1-0") == gw else 0.0)
        byv[v].append((opp, oppv, staff, sc, g["reason"], g["plies"]))
    out = {}
    names = {}
    for g in games:
        names[g["whitePlayerId"]] = g["white"]; names[g["blackPlayerId"]] = g["black"]
    ref = defaultdict(list)
    for opp, oppv, staff, sc, _, _ in byv[25]:
        ref[opp].append(sc)
    for v in VERS:
        rows = byv[v]; P = {}
        P["games (all)"] = len(rows)
        P["score (all)"] = st.mean(x[3] for x in rows)
        P["distinct opponents"] = len({x[0] for x in rows})
        stf = [x for x in rows if x[2]]
        P["vs staff: games, score"] = (len(stf), st.mean(x[3] for x in stf) if stf else None)
        nst = [x for x in rows if not x[2]]
        P["vs non-staff: games, score"] = (len(nst), st.mean(x[3] for x in nst) if nst else None)
        per = defaultdict(list)
        for x in rows:
            per[x[0]].append(x[3])
        common = [o for o in per if o in ref]
        # weight each common opponent by min(n_v, n_25)
        num = den = num25 = 0
        for o in common:
            w = min(len(per[o]), len(ref[o]))
            num += w * st.mean(per[o]); num25 += w * st.mean(ref[o]); den += w
        P["common-opp (with v25): n opps, weight, score, v25 score"] = (len(common), den, num / den if den else None, num25 / den if den else None)
        P["share of games vs opponents also met by v25"] = sum(len(per[o]) for o in common) / len(rows)
        P["loss reasons (all)"] = Counter(x[4] for x in rows if x[3] == 0)
        P["draw reasons (all)"] = Counter(x[4] for x in rows if x[3] == 0.5)
        P["draw share (all)"] = sum(1 for x in rows if x[3] == 0.5) / len(rows)
        P["plies mean (all)"] = st.mean(x[5] for x in rows)
        P["top opponents"] = Counter(x[0][:8] for x in rows).most_common(5)
        P["per opp"] = {names.get(o, o[:8]): v for o, v in per.items()}
        out[v] = P
    return out

if __name__ == "__main__":
    reps = load()
    games = json.load(open(SP + "gg_all_games.json"))
    vof = {}
    for g in games:
        vof[g["id"]] = g["whiteVersion"] if g["whitePlayerId"] == G else g["blackVersion"]
    byv = defaultdict(list)
    for gid, rep in reps.items():
        if gid in vof and rep.get("frames"):
            byv[vof[gid]].append(analyze_game(rep))
    res = {v: summarize(byv[v]) for v in VERS if byv[v]}
    pl = pool(games)
    pickle.dump((res, pl, {v: byv[v] for v in VERS}), open(D + "results.pkl", "wb"))
    with open(D + "raw.md", "w") as out:
        for v in VERS:
            if v not in res: continue
            print("\n## v%d" % v, file=out)
            for k, val in res[v].items():
                print("- %s: %s" % (k, val), file=out)
            print("- POOL:", file=out)
            for k, val in pl[v].items():
                print("  - %s: %s" % (k, val), file=out)
    print(open(D + "raw.md").read())
