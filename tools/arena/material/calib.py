"""Per-piece exposure calibration (view-computable) and exchange accounting.
For every decision of the victim side: after the move, every own non-king piece gets
 lines = fog_lines (unseen squares from which an unaccounted enemy piece could attack it), defended flag,
 moved flag (this move put it there), capval if the move captured, and whether an UNSEEN enemy took it next ply."""
import pickle, sys
from collections import Counter, defaultdict
R = "/Users/ernestogomez/Desktop/fog-of-war-chess-bots"
sys.path.insert(0, R); sys.path.insert(0, R + "/starter")
import chess
from referee import FowBoard
sys.path.insert(0, "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/research/material")
from unseen_losses import fog_lines, captured_square, bal, VAL, SYM, US, GG, SP, OUT

def pieces_after(frames, us):
    b = FowBoard(); hist = []
    for f in frames[1:]:
        mv = chess.Move.from_uci(f["move"]); hist.append((b.copy(stack=False), mv, b.turn, f)); b.push(mv)
    final = b
    pos = lambda k: hist[k][0] if k < len(hist) else final
    rows = []; nmoves = 0
    for i, (P, mv, mover, f) in enumerate(hist):
        if mover != us: continue
        nmoves += 1
        V = frames[i]["white" if us else "black"]
        after = P.copy(stack=False); after.push(mv)
        iscap = P.is_capture(mv); capval = VAL[P.piece_at(captured_square(P, mv)).piece_type] if iscap else 0
        nxt = hist[i + 1] if i + 1 < len(hist) else None
        taken_sq = None; taken_unseen = False
        if nxt is not None and nxt[0].is_capture(nxt[1]):
            taken_sq = captured_square(nxt[0], nxt[1]); taken_unseen = frames[i + 1]["white" if us else "black"][nxt[1].from_square] == "?"
        net3 = bal(pos(i + 3), us) - bal(after, us)  # from after our move: their reply, our reply, their reply... (3 plies)
        gain = bal(pos(i + 3), us) - bal(P, us)       # total swing including our capture
        for s, p in after.piece_map().items():
            if p.color != us or p.piece_type == chess.KING: continue
            true_att = [a for a in after.attackers(not us, s) if V[a] == "?"]
            rows.append(dict(ply=i + 1, sq=s, pt=p.piece_type, val=VAL[p.piece_type], moved=(s == mv.to_square), cap=iscap and s == mv.to_square,
                             capval=capval if s == mv.to_square else 0, defended=after.is_attacked_by(us, s), ndef=len(after.attackers(us, s)),
                             lines=fog_lines(after, us, V, s), true_unseen=len(true_att),
                             true_min=min((VAL[after.piece_at(a).piece_type] for a in true_att), default=None),
                             taken=(taken_sq == s and taken_unseen), taken_seen=(taken_sq == s and not taken_unseen), net3=net3, gain=gain,
                             king_sq=after.king(us)))
    return rows, nmoves

def main():
    ours = pickle.load(open(SP + "replays_cache.pkl", "rb")); gg = pickle.load(open(SP + "gg_games.pkl", "rb"))
    data = {"us": [], "gg": []}; moves = {"us": 0, "gg": 0}; games = {"us": 0, "gg": 0}
    for gid, g in ours.items():
        us = chess.WHITE if g["whitePlayerId"] == US else chess.BLACK
        if (g["whiteVersion"] if us else g["blackVersion"]) != 4: continue
        r, n = pieces_after(g["frames"], us); data["us"] += r; moves["us"] += n; games["us"] += 1
    for gid, g in gg.items():
        m = g["meta"]; us = chess.WHITE if m["whitePlayerId"] == GG else chess.BLACK
        r, n = pieces_after(g["rep"]["frames"], us); data["gg"] += r; moves["gg"] += n; games["gg"] += 1
    pickle.dump((data, moves, games), open(OUT + "calib_rows.pkl", "wb"))
    print(moves, games)

if __name__ == "__main__":
    main()
