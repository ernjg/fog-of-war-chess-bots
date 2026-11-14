"""A scripted UCI engine for tests: legal moves from python-chess, scores from material,
and faults on request.

Run as ``python fake_uci_engine.py``. ``FAKE_UCI`` is a comma-separated list of:

    mute          never answer "uci"
    mute_one=PATH never answer "uci" if this process is the first to create the file PATH
                  (so exactly one engine of a pool is silent)
    die_at=N      exit without a word on the N-th "go" (the handshake's is the first)
    hang_at=N     on the N-th "go", never answer again, not even "stop"
    slow=S        wait S seconds after each depth (so "stop" can arrive mid-search)
    partial       when stopped, report half the moves one depth deeper before "bestmove"
    finish        when stopped, report all the moves one depth deeper before "bestmove"
    bound         when stopped, do the same but give the first line only a bound, as Stockfish
                  does when "stop" interrupts a re-search of its best move
    late=S        answer "stop" only after S seconds
    die_fen=TEXT  exit, as Stockfish does on a position it rejects, when the FEN contains TEXT
    strict        exit on a position Stockfish 19 would reject (kings, pawns, piece counts,
                  or a king that can be captured)
    garbage       sprinkle junk lines into the output
    drop=UCI      never report this move

``FAKE_UCI_SCORES`` is a JSON object mapping moves to centipawn scores, or to a string such
as "mate 1"; other moves score 100 per pawn of material they capture.
"""
import json
import os
import select
import sys
import time

import chess

VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9,
          chess.KING: 0}


def acceptable(board: chess.Board) -> bool:
    """Stockfish 19's own position checks, written out independently of the bot's gate."""
    if board.pawns & (chess.BB_RANK_1 | chess.BB_RANK_8):
        return False
    for color in chess.COLORS:
        counts = {kind: len(board.pieces(kind, color)) for kind in chess.PIECE_TYPES}
        surplus = (max(counts[chess.KNIGHT] - 2, 0) + max(counts[chess.BISHOP] - 2, 0)
                   + max(counts[chess.ROOK] - 2, 0) + max(counts[chess.QUEEN] - 1, 0))
        if counts[chess.KING] != 1 or counts[chess.PAWN] > 8 or surplus > 8 - counts[chess.PAWN]:
            return False
    return not board.is_attacked_by(board.turn, board.king(not board.turn))


def main() -> None:
    options = dict(item.split("=", 1) if "=" in item else (item, "1")
                   for item in os.environ.get("FAKE_UCI", "").split(",") if item)
    if "mute_one" in options:
        try:
            os.close(os.open(options["mute_one"], os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            options["mute"] = "1"
        except FileExistsError:
            pass
    fixed = json.loads(os.environ.get("FAKE_UCI_SCORES", "{}"))
    board = chess.Board()
    goes = 0
    pending = b""

    def out(line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def command(timeout: float | None = None) -> str | None:
        """The next input line, or None if ``timeout`` seconds pass first."""
        nonlocal pending
        while b"\n" not in pending:
            if timeout is not None and not select.select([0], [], [], timeout)[0]:
                return None
            chunk = os.read(0, 4096)
            if not chunk:
                os._exit(0)
            pending += chunk
        line, pending = pending.split(b"\n", 1)
        return line.decode().strip()

    def score(move: chess.Move) -> int:
        if isinstance(fixed.get(move.uci()), str):  # "mate N": ranked by its sign
            return -30000 if "-" in fixed[move.uci()] else 30000
        if move.uci() in fixed:
            return int(fixed[move.uci()])
        if board.is_en_passant(move):
            return 100
        captured = board.piece_at(move.to_square)
        return 100 * VALUES[captured.piece_type] if captured else 0

    while True:
        line = command()
        if line == "uci":
            if "mute" not in options:
                out("id name FakeFish")
                out("option name MultiPV type spin default 1 min 1 max 256")
                out("uciok")
        elif line == "isready":
            out("readyok")
        elif line == "position startpos":
            board = chess.Board()
        elif line.startswith("position fen "):
            fen = line[len("position fen "):]
            board = chess.Board(fen)
            if ("die_fen" in options and options["die_fen"] in fen) or (
                    "strict" in options and not acceptable(board)):
                out("info string CRITICAL ERROR: Command `" + line + "` failed. Reason: test.")
                os._exit(1)
        elif line.startswith("go"):
            goes += 1
            if int(options.get("die_at", 0)) == goes:
                os._exit(1)
            if int(options.get("hang_at", 0)) == goes:
                while True:
                    command()
            # Stockfish says a few long things before each search.
            out("info string Available processors: 0-9 " + "." * 120)
            out("info string NNUE evaluation using nn-0123456789ab.nnue " + "." * 120)
            words = line.split()
            depth = int(words[2]) if words[1:2] == ["depth"] else 1
            moves = [move for move in board.legal_moves if move.uci() != options.get("drop")]
            if not moves:
                out("info depth 0 score " + ("mate 0" if board.is_check() else "cp 0"))
                out("bestmove (none)")
                continue
            ranked = sorted(moves, key=lambda move: (-score(move), move.uci()))

            def report(at_depth: int, some: list[chess.Move]) -> None:
                for move in some:
                    stated = fixed.get(move.uci())
                    out(f"info depth {at_depth} seldepth {at_depth} multipv {ranked.index(move) + 1} "
                        f"score {stated if isinstance(stated, str) else f'cp {score(move)}'} "
                        f"nodes 1 nps 1 hashfull 0 tbhits 0 time 1 pv {move.uci()}")

            for at_depth in range(1, depth + 1):
                if "garbage" in options:
                    out("info string hello")
                    out("nonsense that is not UCI")
                    out("")
                    out("info depth x score cp y pv z")
                report(at_depth, ranked)
                if "slow" in options and at_depth < depth:
                    arrived = command(float(options["slow"]))
                    if arrived == "quit":
                        os._exit(0)
                    if arrived == "stop":
                        if "late" in options:
                            time.sleep(float(options["late"]))
                        if "partial" in options:
                            report(at_depth + 1, ranked[:max(1, len(ranked) // 2)])
                        if "finish" in options:
                            report(at_depth + 1, ranked)
                        if "bound" in options:
                            out(f"info depth {at_depth + 1} seldepth {at_depth + 1} multipv 1 score cp "
                                f"{score(ranked[0]) + 7} lowerbound nodes 1 nps 1 hashfull 0 tbhits 0 "
                                f"time 1 pv {ranked[0].uci()}")
                            report(at_depth + 1, ranked[1:])
                        break
            out(f"bestmove {ranked[0].uci()}")
        elif line == "quit":
            os._exit(0)


if __name__ == "__main__":
    main()
