"""The Stockfish search: move classification, the engine gate, and the averaging.

Most tests use the scripted engine. The ones marked ``real`` need Stockfish 19 and run
only when FOW_STOCKFISH names a binary (see docs/obscuro.md).
"""
from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402
import numpy as np  # noqa: E402

from fow.obscuro.belief import Belief, fit_to_view, project  # noqa: E402
from fow.obscuro.engine import EnginePool, Job, cp_value  # noqa: E402
from fow.obscuro.rules import side_to_move_wins  # noqa: E402
from fow.obscuro.stockfish_search import (ATTACKED_WEIGHT, MAX_DEPTH, WIN, classify,  # noqa: E402
                                          engine_accepts, engine_fen, king_capturable_after,
                                          no_safe_reply, stockfish_search)
from referee import FowBoard, fow_moves, observation  # noqa: E402

FAKE = [sys.executable, str(Path(__file__).with_name("fake_uci_engine.py"))]
STOCKFISH = os.environ.get("FOW_STOCKFISH", "")
real = pytest.mark.skipif(not Path(STOCKFISH).is_file(), reason="FOW_STOCKFISH is not a Stockfish binary")

CASTLE_THROUGH_ATTACK = "r3k2r/8/8/8/8/5r2/8/R3K2R w KQkq - 0 1"   # f1 is attacked
CASTLE_OUT_OF_CHECK = "r3k2r/8/8/8/8/4r3/8/R3K2R w KQkq - 0 1"     # the king is attacked
CASTLE_INTO_ATTACK = "r3k2r/8/8/8/8/6r1/8/R3K2R w KQkq - 0 1"      # g1 is attacked
PINNED_BISHOP = "4k3/8/8/8/4r3/8/4B3/4K3 w - - 0 1"
EN_PASSANT_EXPOSES_KING = "8/8/8/K2pP2r/8/8/8/4k3 w - d6 0 1"
CHECKMATED = "7k/5QQ1/8/8/8/8/8/K7 b - - 0 1"
STALEMATED = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
MATED_BUT_FOR_CASTLING = "r3k3/8/8/8/8/8/8/3RRRK1 b q - 0 1"       # only O-O-O saves the king
HANDMADE = [CASTLE_THROUGH_ATTACK, CASTLE_OUT_OF_CHECK, CASTLE_INTO_ATTACK, PINNED_BISHOP,
            EN_PASSANT_EXPOSES_KING, CHECKMATED, STALEMATED, MATED_BUT_FOR_CASTLING,
            "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1", "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1"]


def playout_positions(seed: int, games: int, plies: int) -> list[FowBoard]:
    """Positions from random Fog of War games in which nobody leaves a king capturable."""
    rng = random.Random(seed)
    found = []
    for _ in range(games):
        board = FowBoard()
        for _ in range(plies):
            safe = [move for move in fow_moves(board) if not king_capturable_after(board, move)]
            if not safe:
                break
            board.push(rng.choice(safe))
            found.append(board.copy(stack=False))
    return found


def uci(board: FowBoard, indices) -> set[str]:
    moves = fow_moves(board)
    return {moves[i].uci() for i in indices}


def test_classify_matches_orthodox_chess_and_brute_force() -> None:
    boards = playout_positions(11, games=25, plies=60) + [FowBoard(fen) for fen in HANDMADE]
    seen = {"legal": 0, "suicide": 0, "fow_only": 0}
    for board in boards:
        moves = fow_moves(board)
        classes = classify(board, moves)
        assert classes is not None
        orthodox = set(chess.Board(board.fen(en_passant="fen")).legal_moves)
        for index, move in enumerate(moves):
            capturable = king_capturable_after(board, move)
            if move in orthodox:
                assert index in classes.legal and not capturable
            elif capturable:
                assert index in classes.suicide
            else:
                assert index in classes.fow_only and board.is_castling(move)
        assert sorted(classes.legal + classes.suicide + classes.fow_only) == list(range(len(moves)))
        for name in seen:
            seen[name] += len(getattr(classes, name))
    assert all(seen.values()), seen  # every class was exercised


def test_classify_handmade_castling_and_pins() -> None:
    def classes_of(fen):
        board = FowBoard(fen)
        found = classify(board, fow_moves(board))
        return {name: uci(board, getattr(found, name)) for name in ("legal", "suicide", "fow_only")}

    through = classes_of(CASTLE_THROUGH_ATTACK)
    assert "e1g1" in through["fow_only"] and "e1c1" in through["legal"]
    assert "e1f1" in through["suicide"] and "e1f2" in through["suicide"]
    assert classes_of(CASTLE_OUT_OF_CHECK)["fow_only"] == {"e1g1", "e1c1"}
    into = classes_of(CASTLE_INTO_ATTACK)
    assert "e1g1" in into["suicide"] and "e1c1" in into["legal"]
    pinned = classes_of(PINNED_BISHOP)
    assert {"e2d3", "e2f1", "e2a6"} <= pinned["suicide"] and "e1d1" in pinned["legal"]
    assert "e5d6" in classes_of(EN_PASSANT_EXPOSES_KING)["suicide"]


def test_classify_rejects_states_that_contradict_our_view() -> None:
    board = FowBoard()
    assert classify(board, [chess.Move.from_uci("e2e5")]) is None      # not playable there
    assert classify(board, [chess.Move.from_uci("e7e5")]) is None      # not our turn there
    king_en_prise = FowBoard("4k3/4Q3/8/8/8/8/8/4K3 w - - 0 1")
    assert classify(king_en_prise, fow_moves(king_en_prise)) is None   # the game would be over


def test_no_safe_reply_matches_brute_force() -> None:
    """True exactly where every move of the side to move loses its king, castling included."""
    near_the_end = ["7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "7k/5QQ1/8/8/8/8/8/K7 b - - 0 1",
                    "k7/2Q5/1K6/8/8/8/8/8 b - - 0 1", "k7/1Q6/1K6/8/8/8/8/8 b - - 0 1",
                    "6k1/5ppp/8/8/8/8/8/R3K2R b - - 0 1", "R5k1/5ppp/8/8/8/8/8/4K3 b - - 0 1",
                    "5rk1/5Npp/8/8/8/8/8/4K2Q b - - 0 1", "r3k3/8/8/8/8/8/8/3RRRK1 b q - 0 1",
                    "r3k2r/8/8/8/8/8/3PPP2/3RKR2 b kq - 0 1"]
    boards = (playout_positions(5, games=15, plies=70)
              + [FowBoard(fen) for fen in HANDMADE + near_the_end])
    terminal = 0
    for board in boards:
        doomed = True
        for move in fow_moves(board):
            board.push(move)
            doomed = doomed and side_to_move_wins(board)
            board.pop()
        assert no_safe_reply(board) is doomed, board.fen()
        terminal += doomed
    assert terminal >= 6
    # Castling out of check saves the king only if the square it lands on is safe.
    assert no_safe_reply(FowBoard("r3k3/8/8/8/8/8/8/2RRRRK1 b q - 0 1"))
    assert no_safe_reply(FowBoard(CHECKMATED)) and no_safe_reply(FowBoard(STALEMATED))
    assert not no_safe_reply(FowBoard(MATED_BUT_FOR_CASTLING))  # O-O-O gets out
    assert not no_safe_reply(FowBoard())


GATE_CASES = [  # (FEN, does Stockfish 19 take it) as measured against the real engine.
    # In none of the rejected material cases is a king attacked: each fails for its own reason.
    ("4k3/4Q3/8/8/8/8/8/4K3 w - - 0 1", False),                        # king can be captured
    ("8/8/8/8/8/8/3K4/3k4 w - - 0 1", False),                          # ... by the other king
    ("8/8/8/8/8/8/8/4K3 w - - 0 1", False),                            # no black king
    ("4k3/8/8/8/8/8/8/3KK3 w - - 0 1", False),                         # two white kings
    ("4k3/8/8/8/8/8/PPPPPPPP/QQ2K3 w - - 0 1", False),                 # a second queen, 8 pawns
    ("4k3/8/8/8/8/2NNN3/PPPPPPPP/4K3 w - - 0 1", False),               # a third knight, 8 pawns
    ("4k3/8/8/8/8/8/PPPPPPPP/BBB1K3 w - - 0 1", False),                # a third bishop, 8 pawns
    ("4k3/8/8/8/8/8/PPPPPPPP/RRR1K3 w - - 0 1", False),                # a third rook, 8 pawns
    ("4k3/pppppppp/8/8/8/8/8/1nnnK3 b - - 0 1", False),                # the same rule for Black
    ("4k3/8/8/8/8/8/2NNN3/PPPPPPPK w - - 0 1", False),                 # pawns on the first rank
    ("4k3/8/8/8/P7/8/PPPPPPPP/4K3 w - - 0 1", False),                  # nine pawns
    ("P3k3/8/8/8/8/8/8/4K3 w - - 0 1", False),                         # pawn on the eighth rank
    ("4k3/8/8/8/8/5n2/3r4/3qK2r w - - 0 1", True),                     # "impossible" triple check
    ("4k3/8/8/8/8/2NNN3/PPPPPPP1/4K3 w - - 0 1", True),                # a third knight, 7 pawns
    ("4k3/8/8/8/8/8/PPPPPPP1/QQ2K3 w - - 0 1", True),                  # a second queen, 7 pawns
    ("4k3/8/8/8/8/8/8/4K2R w - - 0 1", True),
    ("4k3/8/8/8/8/8/8/4K2R w - - 99 80", True),                        # clock at its last ply
    (chess.STARTING_FEN, True),
]


def test_engine_gate_mirrors_stockfish() -> None:
    for fen, accepted in GATE_CASES:
        assert engine_accepts(FowBoard(fen)) is accepted, fen
    for board in playout_positions(3, games=20, plies=80):
        assert engine_accepts(board)  # positions reached by play always pass


def test_engine_fen_passes_a_real_clock_and_replaces_an_impossible_one() -> None:
    for clock in (0, 42, 99):  # the state's own count: Stockfish should know it
        assert engine_fen(FowBoard(f"4k3/8/8/8/8/8/8/4K2R w - - {clock} 80")).split()[4] == str(clock)
    for clock in (100, 150):   # the game would be over: unknown, so keep the draw out of reach
        fen = engine_fen(FowBoard(f"4k3/8/8/8/8/8/8/4K2R w - - {clock} 80"))
        assert int(fen.split()[4]) + MAX_DEPTH == 99
    assert engine_fen(FowBoard()) == chess.STARTING_FEN


@pytest.fixture
def start(monkeypatch):
    pools = []

    def _start(count: int = 2, faults: str = "", scores: str = "{}"):
        monkeypatch.setenv("FAKE_UCI", faults)
        monkeypatch.setenv("FAKE_UCI_SCORES", scores)
        pool = EnginePool.start(FAKE, count, time.monotonic() + 5)
        pools.append(pool)
        return pool

    yield _start
    for pool in pools:
        pool.close()


def rook_states(*rook_squares: str) -> list[FowBoard]:
    """White Ke1 and Ra1 against Ke8 and one black rook, on a different square per state."""
    states = []
    for square in rook_squares:
        board = FowBoard("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
        board.set_piece_at(chess.parse_square(square), chess.Piece(chess.ROOK, chess.BLACK))
        states.append(board)
    return states


def test_search_takes_the_hanging_queen(start) -> None:
    state = FowBoard("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
    result = stockfish_search(start(), [state], fow_moves(state), chess.WHITE, 1.0, random.Random(0))
    assert result.move == chess.Move.from_uci("e4d5")
    assert result.value == pytest.approx(cp_value(900)) and result.risk == 0
    assert (result.scanned, result.sampled, result.roots) == (1, 1, 1)


def test_value_is_the_mean_with_a_loss_where_the_king_is_taken(start) -> None:
    # Ke2 scores 5000 where it is safe, and walks into the rook on h2 in one state of four.
    states = rook_states("h2", "h3", "h4", "h5")
    moves = fow_moves(states[0])
    result = stockfish_search(start(scores='{"e1e2": 5000}'), states, moves, chess.WHITE, 1.0,
                              random.Random(0))
    index = moves.index(chess.Move.from_uci("e1e2"))
    assert result.values[index] == pytest.approx((3 * cp_value(5000) - 1) / 4)
    assert result.move == moves[index] and result.risk == pytest.approx(0.25)
    assert result.roots == 4

    # In half of the states it is a loss; then a quiet move worth 0 is better than -0.009.
    result = stockfish_search(start(scores='{"e1e2": 5000}'), rook_states("h2", "g2", "h4", "h5"),
                              moves, chess.WHITE, 1.0, random.Random(0))
    assert result.values[index] == pytest.approx((2 * cp_value(5000) - 2) / 4)
    assert result.move != moves[index] and result.value == pytest.approx(0.0, abs=1e-6)


def test_the_larger_of_two_overwhelming_scores_is_preferred(start) -> None:
    """Both moves keep a won position; the one Stockfish rates higher must still win."""
    state = rook_states("h5")[0]
    moves = fow_moves(state)
    result = stockfish_search(start(scores='{"e1d1": 1700, "a1a7": 2600, "a1a6": 1900}'), [state],
                              moves, chess.WHITE, 1.0, random.Random(0))
    assert result.move.uci() == "a1a7"
    assert 0.97 < result.values[moves.index(chess.Move.from_uci("e1d1"))] < result.value < 0.99


def test_mate_in_one_that_castling_escapes_is_not_trusted(start) -> None:
    """Re5 is mate to Stockfish. Here Black may castle out of the check, so on that state
    the move is worth no more than the worst of the others; without the castling right
    it wins."""
    scores = '{"h5e5": "mate 1", "g1h1": -40, "d1d7": 70}'
    escapes = FowBoard("r3k3/8/8/7R/8/8/8/3R1RK1 w q - 0 1")
    moves = fow_moves(escapes)
    check = moves.index(chess.Move.from_uci("h5e5"))
    result = stockfish_search(start(scores=scores), [escapes], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.roots == 1 and result.values[check] == pytest.approx(cp_value(-40))
    assert result.move.uci() == "d1d7"  # the state still speaks for the other moves

    trapped = FowBoard("r3k3/8/8/7R/8/8/8/3R1RK1 w - - 0 1")
    result = stockfish_search(start(scores=scores), [trapped], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.move.uci() == "h5e5" and result.value == WIN

    # Where the mate is real in one state of four, the move is not taken for a sure win
    # on the strength of that one: the three states that refute it count as well.
    result = stockfish_search(start(scores=scores), [escapes, escapes.copy(), escapes.copy(), trapped],
                              moves, chess.WHITE, 1.0, random.Random(0))
    assert (result.sampled, result.roots) == (4, 4)
    assert result.values[check] == pytest.approx((3 * cp_value(-40) + WIN) / 4)


def test_a_real_win_survives_beside_a_mate_that_castling_escapes(start) -> None:
    """Qe6 leaves Black no safe reply at all (c8 is covered too), while Re5 only looks
    like mate. The state must keep its win."""
    state = FowBoard("r3k3/8/7Q/7R/8/8/8/3R1RK1 w q - 0 1")
    moves = fow_moves(state)
    result = stockfish_search(start(scores='{"h5e5": "mate 1", "h6e6": "mate 1"}'), [state], moves,
                              chess.WHITE, 1.0, random.Random(0))
    by_move = dict(zip([move.uci() for move in moves], result.values, strict=True))
    assert by_move["h6e6"] == WIN and by_move["h5e5"] < 0.5
    assert result.move.uci() == "h6e6"


def test_fog_only_castling_is_scored_from_the_position_after_it(start) -> None:
    state = FowBoard(CASTLE_THROUGH_ATTACK)
    moves = fow_moves(state)
    result = stockfish_search(start(), [state], moves, chess.WHITE, 1.0, random.Random(0))
    castle = moves.index(chess.Move.from_uci("e1g1"))
    # After O-O the black rook takes the rook on f1: 500 for the opponent, so -that for us.
    assert result.values[castle] == pytest.approx(-cp_value(500))
    assert result.values[moves.index(chess.Move.from_uci("e1f1"))] == -1.0  # into the rook


def test_fog_only_castling_that_leaves_no_safe_reply_is_a_win(start) -> None:
    """White is in check from the knight and castles out of it, which only this game
    allows. The rook then attacks the king on f8, and nothing Black has can block the
    file, take the rook or step off it: Black loses its king whatever it plays."""
    state = FowBoard("4rkr1/4p1p1/8/8/8/8/2n5/4K2R w K - 0 1")
    moves = fow_moves(state)
    castle = moves.index(chess.Move.from_uci("e1g1"))
    assert classify(state, moves).fow_only == (castle,)
    result = stockfish_search(start(), [state], moves, chess.WHITE, 1.0, random.Random(0))
    assert result is not None and result.roots == 1
    assert result.values[castle] == WIN and result.move.uci() == "e1g1"


def test_stalemating_the_opponent_counts_as_a_win(start) -> None:
    state = FowBoard("7k/4Q3/6K1/8/8/8/8/8 w - - 0 1")
    moves = fow_moves(state)
    result = stockfish_search(start(), [state], moves, chess.WHITE, 1.0, random.Random(0))
    wins = set()
    for move in moves:  # by brute force: after it, every black move leaves the king capturable
        if king_capturable_after(state, move):
            continue  # ours would be taken first
        state.push(move)
        if all(king_capturable_after(state, reply) for reply in fow_moves(state)):
            wins.add(move.uci())
        state.pop()
    assert {"e7f7", "e7e6", "e7e8", "e7g7"} <= wins  # two stalemates and two mates among them
    for index, move in enumerate(moves):
        assert (result.values[index] == WIN) is (move.uci() in wins), move
    assert result.move.uci() in wins and result.value == WIN


def test_does_not_repeat_the_same_move_when_winning(start) -> None:
    state = rook_states("h5")[0]
    moves = fow_moves(state)
    scores = '{"a1a8": 300, "a1a7": 290}'
    plain = stockfish_search(start(scores=scores), [state], moves, chess.WHITE, 1.0, random.Random(0))
    assert plain.move.uci() == "a1a8" and not plain.repeat_avoided
    counts = [1 if move.uci() == "a1a8" else 0 for move in moves]
    again = stockfish_search(start(scores=scores), [state], moves, chess.WHITE, 1.0,
                             random.Random(0), repeat_counts=counts)
    assert again.move.uci() == "a1a7" and again.repeat_avoided


def test_returns_none_when_it_has_nothing_to_go_on(start) -> None:
    state = rook_states("h5")[0]
    moves = fow_moves(state)
    rng = random.Random(0)
    missing = EnginePool.start([str(ROOT / "no-such-engine")], 2, time.monotonic() + 1)
    assert stockfish_search(missing, [state], moves, chess.WHITE, 1.0, rng) is None
    pool = start()
    assert stockfish_search(pool, [state], moves, chess.WHITE, 0.05, rng) is None       # no time
    assert stockfish_search(pool, [], moves, chess.WHITE, 1.0, rng) is None             # no states
    assert stockfish_search(pool, [FowBoard()], moves, chess.WHITE, 1.0, rng) is None   # wrong view
    assert pool.ready_count() == 2  # none of that touched the engines


def test_survives_engines_dying_mid_search(start) -> None:
    states = rook_states("h3", "h4", "h5")
    moves = fow_moves(states[0])
    one_job_each = start(1, "die_at=3")  # handshake, one state, then the engine exits
    result = stockfish_search(one_job_each, states, moves, chess.WHITE, 1.0, random.Random(0))
    assert (result.sampled, result.roots) == (3, 1)
    assert stockfish_search(one_job_each, states, moves, chess.WHITE, 1.0, random.Random(0)) is None
    dies_at_once = start(2, "die_at=2")
    assert stockfish_search(dies_at_once, states, moves, chess.WHITE, 1.0, random.Random(0)) is None


def test_a_state_missing_a_move_score_is_left_out(start) -> None:
    states = rook_states("h3", "h4")
    moves = fow_moves(states[0])
    pool = start(1, "drop=a1a8")  # the engine never reports this legal move
    assert stockfish_search(pool, states, moves, chess.WHITE, 1.0, random.Random(0)) is None


def test_respects_its_budget(start) -> None:
    states = playout_positions(1, games=1, plies=12)[-1:]
    board = states[0]
    pool = start(2, "slow=0.05")  # the engine would need 0.55 s to reach its depth
    began = time.monotonic()
    result = stockfish_search(pool, states, fow_moves(board), board.turn, 0.4, random.Random(0))
    assert 0.3 < time.monotonic() - began < 0.45
    assert result is not None and result.depth[0] >= 1


def test_states_the_engine_would_reject_are_scanned_but_not_sent(start) -> None:
    """The scripted engine exits here, as Stockfish does, on a position it cannot take.
    Each state's values must also stay with that state: Ke2 loses the king on the first."""
    impossible = rook_states("h4")[0]
    impossible.set_piece_at(chess.H1, chess.Piece(chess.PAWN, chess.BLACK))  # a pawn on rank 1
    states = [rook_states("h2")[0], impossible, rook_states("h5")[0]]
    assert [engine_accepts(state) for state in states] == [True, False, True]
    moves = fow_moves(states[0])
    assert all(set(moves) <= set(fow_moves(state)) for state in states)
    pool = start(2, "strict", scores='{"e1e2": 300}')
    result = stockfish_search(pool, states, moves, chess.WHITE, 1.0, random.Random(0))
    assert (result.scanned, result.sampled, result.roots) == (3, 2, 2)
    assert pool.deaths == 0 and pool.ready_count() == 2
    index = moves.index(chess.Move.from_uci("e1e2"))
    assert result.risks[index] == pytest.approx(1 / 3)                    # of the three scanned
    assert result.values[index] == pytest.approx(-1 / 3 + 2 / 3 * cp_value(300))  # one safe state scored


def test_states_where_every_move_loses_say_nothing_on_their_own(start) -> None:
    """Such a state needs no engine. If the engine fails on every other state, the search
    must hand over to the PCFR+ search, not pick among moves it knows nothing about."""
    mated = FowBoard("4k3/4r3/8/8/8/8/4q3/R3K3 w - - 0 1")  # our king cannot be saved here
    normal = rook_states("h5")[0]
    moves = [move for move in fow_moves(normal) if move in set(fow_moves(mated))]
    assert classify(mated, moves).legal == () and classify(mated, moves).fow_only == ()
    dead_on_arrival = start(2, "die_at=2")
    assert stockfish_search(dead_on_arrival, [mated, normal], moves, chess.WHITE, 1.0,
                            random.Random(0)) is None
    # When every scanned state is like that, any move is as good as another: answer.
    assert stockfish_search(start(2), [mated], moves, chess.WHITE, 1.0, random.Random(0)) is not None


def test_en_passant_and_promotions_go_through_the_engine(start) -> None:
    en_passant = FowBoard("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
    moves = fow_moves(en_passant)
    result = stockfish_search(start(), [en_passant], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.move.uci() == "e5d6" and result.value == pytest.approx(cp_value(100))
    exposed = FowBoard(EN_PASSANT_EXPOSES_KING)
    moves = fow_moves(exposed)
    result = stockfish_search(start(), [exposed], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.values[moves.index(chess.Move.from_uci("e5d6"))] == -1.0
    promotion = FowBoard("3r4/4P3/8/8/8/8/8/k3K3 w - - 0 1")
    moves = fow_moves(promotion)
    assert {"e7e8q", "e7e8n", "e7d8q", "e7d8r", "e7d8b", "e7d8n"} <= {move.uci() for move in moves}
    result = stockfish_search(start(), [promotion], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.roots == 1 and result.move.uci().startswith("e7d8")  # takes the rook, promoting


def test_stalemate_counts_as_a_win_whatever_the_material(start) -> None:
    # Black has king and three blocked pawns; Qf7 leaves it no safe move.
    state = FowBoard("7k/4Q3/6K1/p1p1p3/P1P1P3/8/8/8 w - - 0 1")
    moves = fow_moves(state)
    result = stockfish_search(start(), [state], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.values[moves.index(chess.Move.from_uci("e7f7"))] == WIN


def test_a_quiet_winning_move_at_ply_99_is_only_a_draw(start) -> None:
    """The referee declares the fifty-move draw before the opponent has to answer, so at 99
    plies without progress only a capture or a pawn move keeps the game going."""
    scores = '{"e7e6": 300, "a2a3": 200}'
    last_ply = FowBoard("7k/4Q3/6K1/8/8/8/P7/8 w - - 99 80")
    moves = fow_moves(last_ply)
    result = stockfish_search(start(scores=scores), [last_ply], moves, chess.WHITE, 1.0, random.Random(0))
    by_move = dict(zip([move.uci() for move in moves], result.values, strict=True))
    assert by_move["e7f7"] == 0.0 and by_move["e7e6"] == 0.0   # stalemate, and a good quiet move
    assert by_move["a2a3"] == pytest.approx(cp_value(200))     # the pawn move resets the count
    assert by_move["g6h7"] == -1.0                             # losing the king still loses
    assert result.move.uci() == "a2a3"

    one_ply_earlier = FowBoard("7k/4Q3/6K1/8/8/8/P7/8 w - - 98 80")
    result = stockfish_search(start(scores=scores), [one_ply_earlier], moves, chess.WHITE, 1.0,
                              random.Random(0))
    by_move = dict(zip([move.uci() for move in moves], result.values, strict=True))
    assert by_move["e7f7"] == WIN and by_move["e7e6"] == pytest.approx(cp_value(300))


def projected_positions(seed: int, count: int) -> list[FowBoard]:
    """Belief states as a repair and the top-up after it leave them: one game's board
    overwritten with another game's view and fitted to it, and states grown from those."""
    boards = playout_positions(seed, games=12, plies=50)
    rng = random.Random(seed)
    found = []
    while len(found) < count:
        guess, truth = rng.choice(boards), rng.choice(boards)
        side = truth.turn
        obs = observation(truth, side)
        repaired = fit_to_view(project(guess, obs, side, side), obs, side, rng)
        found.append(repaired)
        if len(found) % 10 == 0:  # now and then, also what the top-up makes of it
            belief = Belief(side, rng=rng)
            belief.states, belief.exact, belief._unchecked = [repaired], False, True
            belief.replenish(obs)
            found.extend(belief.states[:5])
    return found[:count]


@pytest.fixture(scope="module")
def stockfish():
    pool = EnginePool.start([STOCKFISH], 2, time.monotonic() + 20, cwd=str(Path(STOCKFISH).parent))
    yield pool
    pool.close()


@real
def test_real_engine_takes_every_position_the_gate_lets_through(stockfish) -> None:
    played = playout_positions(21, games=10, plies=60)
    repaired = projected_positions(22, 400)
    # A repair keeps the opponent's material possible, so nearly all of them pass. (What
    # the gate rejects is tried against the engine in the next test.)
    assert sum(map(engine_accepts, repaired)) > 0.9 * len(repaired)
    accepted = [board for board in played + repaired if engine_accepts(board)]
    results = stockfish.run([Job(engine_fen(board), 1) for board in accepted],
                            time.monotonic() + 120, 0.05, 1.0)
    assert stockfish.deaths == 0 and stockfish.ready_count() == 2
    assert all(result is not None for result in results)
    for board, result in zip(accepted, results, strict=True):
        orthodox = {move.uci() for move in chess.Board(board.fen(en_passant="fen")).legal_moves}
        assert set(result.scores) == orthodox and result.no_moves == (not orthodox)
        if orthodox:
            assert result.complete_depth(sorted(orthodox)) == 1


@real
def test_real_engine_exits_on_what_the_gate_rejects() -> None:
    """Why the gate exists. If this fails, Stockfish changed and the gate needs another look."""
    for fen, accepted in GATE_CASES:
        pool = EnginePool.start([STOCKFISH], 1, time.monotonic() + 20, cwd=str(Path(STOCKFISH).parent))
        try:
            (result,) = pool.run([Job(fen, 1)], time.monotonic() + 10, 0.05, 1.0)
            assert (result is not None) is accepted, fen
            assert (pool.ready_count() == 1) is accepted, fen
            if not accepted:
                assert "CRITICAL ERROR" in pool.failure or "exited" in pool.failure
        finally:
            pool.close()


@real
def test_real_engine_stopped_early_reports_only_finished_iterations(stockfish) -> None:
    board = chess.Board("r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 8")
    moves = [move.uci() for move in board.legal_moves]
    for slice_seconds in (0.0002, 0.002, 0.01, 0.05, 0.2):
        results = stockfish.run([Job(board.fen(), 30)] * 6, time.monotonic() + 30,
                                slice_seconds, slice_seconds)
        for result in results:
            assert result is not None and result.stopped
            depth = result.complete_depth(moves)
            if depth is None:  # stopped before depth 1 was done: nothing, rather than placeholders
                assert slice_seconds < 0.05
                continue
            assert set(result.scores) == set(moves)
            # Every move was scored at every depth up to the last finished one, and no deeper.
            assert all(sorted(found) == list(range(1, depth + 1)) for found in result.scores.values())
            # Not the "score cp 0" placeholders: this position is not dead level for all moves.
            assert len({found[depth] for found in result.scores.values()}) > 5
    assert stockfish.deaths == 0 and stockfish.ready_count() == 2


@real
def test_real_search_finds_tactics_and_keeps_the_king_safe(stockfish) -> None:
    hanging = FowBoard("r1bqkbnr/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 1")
    hanging.set_piece_at(chess.H5, None)
    hanging.set_piece_at(chess.G5, chess.Piece(chess.QUEEN, chess.WHITE))  # the queen hangs to d8
    result = stockfish_search(stockfish, [hanging], fow_moves(hanging), chess.BLACK, 1.0,
                              random.Random(0))
    assert result.move.uci() == "d8g5" and result.value > 0.5 and result.depth[0] >= 4

    states = rook_states("h2", "h3", "h4", "h5")
    moves = fow_moves(states[0])
    result = stockfish_search(stockfish, states, moves, chess.WHITE, 1.0, random.Random(0))
    # A level position where Ke2 is safe, and a lost king in one state of four.
    assert result.values[moves.index(chess.Move.from_uci("e1e2"))] == pytest.approx(-0.25, abs=0.05)
    assert result.risk == 0 and not math.isnan(result.value)
    assert stockfish.deaths == 0


@real
def test_real_engine_scores_stalemate_as_exactly_zero_so_that_it_counts_as_a_win(stockfish) -> None:
    """The stalemate rule is applied to moves Stockfish scores as exactly 0. If it ever
    scored a stalemating move differently, the move would be valued as a draw."""
    for fen in ("7k/4Q3/6K1/8/8/8/8/8 w - - 0 1", "7k/4Q3/6K1/p1p1p3/P1P1P3/8/8/8 w - - 0 1"):
        state = FowBoard(fen)
        moves = fow_moves(state)
        result = stockfish_search(stockfish, [state], moves, chess.WHITE, 1.0, random.Random(0))
        by_move = dict(zip([move.uci() for move in moves], result.values, strict=True))
        assert by_move["e7f7"] == WIN     # stalemate: 0 to Stockfish, a win here
        assert by_move["e7e8"] == WIN     # mate in one, checked against this game's rules
        assert by_move["g6h7"] == -1.0    # into the king
        assert result.value == WIN and result.roots == 1
    # What Stockfish calls mate in one, the king escapes by castling: not to be believed.
    escapes = FowBoard("r3k3/8/8/7R/8/8/8/3R1RK1 w q - 0 1")
    moves = fow_moves(escapes)
    result = stockfish_search(stockfish, [escapes], moves, chess.WHITE, 1.0, random.Random(0))
    by_move = dict(zip([move.uci() for move in moves], result.values, strict=True))
    assert by_move["h5e5"] == min(value for value in by_move.values() if value > -1.0)
    assert result.move.uci() != "h5e5" and result.roots == 1
    trapped = FowBoard("r3k3/8/8/7R/8/8/8/3R1RK1 w - - 0 1")
    result = stockfish_search(stockfish, [trapped], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.move.uci() == "h5e5" and result.value == WIN
    assert stockfish.deaths == 0


@real
def test_real_engine_names_en_passant_and_promotions_as_we_do(stockfish) -> None:
    """A state counts as scored only if every one of our legal moves is found in the
    engine's report under the same name."""
    en_passant = FowBoard("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
    moves = fow_moves(en_passant)
    assert chess.Move.from_uci("e5d6") in moves
    result = stockfish_search(stockfish, [en_passant], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.roots == 1 and result.move in moves

    promotion = FowBoard("3r4/4P3/8/8/8/8/8/k3K3 w - - 0 1")
    moves = fow_moves(promotion)
    assert {"e7e8q", "e7e8n", "e7d8q", "e7d8r", "e7d8b", "e7d8n"} <= {move.uci() for move in moves}
    result = stockfish_search(stockfish, [promotion], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.roots == 1 and result.move.uci() == "e7d8q" and result.value > 0.3  # a queen up

    castling = FowBoard("r3k2r/pppq1ppp/2npbn2/2b1p3/2B1P3/2NPBN2/PPPQ1PPP/R3K2R w KQkq - 0 8")
    moves = fow_moves(castling)
    assert {"e1g1", "e1c1"} <= {move.uci() for move in moves}
    result = stockfish_search(stockfish, [castling], moves, chess.WHITE, 1.0, random.Random(0))
    assert result.roots == 1
    assert stockfish.deaths == 0


@real
def test_real_search_on_played_positions(stockfish) -> None:
    rng = random.Random(4)
    for board in rng.sample(playout_positions(31, games=6, plies=50), 12):
        if side_to_move_wins(board):
            continue
        moves = fow_moves(board)
        result = stockfish_search(stockfish, [board], moves, board.turn, 0.3, rng)
        assert result is not None and result.move in moves
        assert len(result.values) == len(moves) and all(-1.0 <= v <= 1.0 for v in result.values)
    assert stockfish.deaths == 0


def evidence(scan_attacked, scan_suicide, root_rows, root_values):
    """Evidence whose scored states are the scanned states at ``root_rows``."""
    from fow.obscuro.stockfish_search import Evidence
    scan_attacked = np.array(scan_attacked, dtype=bool)
    scan_suicide = np.array(scan_suicide, dtype=bool)
    return Evidence(scan_attacked, scan_suicide, scan_attacked[root_rows], scan_suicide[root_rows],
                    np.array(root_values, dtype=float), len(root_rows), ())


def test_weigh_is_the_plain_mean_when_nothing_is_reweighted() -> None:
    from fow.obscuro.stockfish_search import weigh
    # Three states, all scored; move 0 loses the king on the first.
    found = evidence([False, False, False], [[1, 0], [0, 0], [0, 0]], [0, 1, 2],
                     [[-1.0, 0.2], [0.6, 0.1], [0.3, -0.4]])
    value, risk = weigh(found, attacked_weight=1.0)
    assert value == pytest.approx([(-1.0 + 0.6 + 0.3) / 3, (0.2 + 0.1 - 0.4) / 3])
    assert risk == pytest.approx([1 / 3, 0.0])


def test_weigh_takes_risk_from_all_scanned_states_and_value_from_scored_ones() -> None:
    from fow.obscuro.stockfish_search import weigh
    # Four scanned, the last two scored. Move 0 loses the king on one unscored state.
    found = evidence([False] * 4, [[1, 0], [0, 0], [0, 0], [0, 0]], [2, 3], [[0.5, 0.0], [0.7, 0.2]])
    value, risk = weigh(found, attacked_weight=1.0)
    assert risk == pytest.approx([0.25, 0.0])
    assert value == pytest.approx([-0.25 + 0.75 * 0.6, 0.1])
    # A move that loses the king wherever it was scored has no value to fall back on.
    doomed = evidence([False, False], [[1, 0], [1, 0]], [0, 1], [[-1.0, 0.0], [-1.0, 0.1]])
    value, risk = weigh(doomed, attacked_weight=1.0)
    assert value[0] == -1.0 and risk[0] == 1.0


def test_weigh_gives_a_move_without_a_safe_scored_state_the_lowest_known_value() -> None:
    from fow.obscuro.stockfish_search import weigh
    # Four scanned; only the first is scored, and there move 0 loses the king.
    found = evidence([False] * 4, [[1, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]], [0],
                     [[-1.0, 0.3, 0.1]])
    value, risk = weigh(found, attacked_weight=1.0)
    assert risk == pytest.approx([0.25, 0.0, 0.0])
    assert value[0] == pytest.approx(-0.25 + 0.75 * 0.1)  # as good as the worst known move, at best
    assert value[0] < value[2] < value[1]


def test_search_uses_the_default_weight_for_attacked_states(start) -> None:
    """Pins the default: in one state of four our king is attacked by a rook we cannot see."""
    assert ATTACKED_WEIGHT == 6.0
    attacked = FowBoard("4k3/8/8/8/8/8/8/R3K2r w - - 0 1")
    states = rook_states("h3", "h4", "h5") + [attacked]
    moves = fow_moves(states[0])
    assert classify(attacked, moves).legal and attacked.is_check()
    result = stockfish_search(start(), states, moves, chess.WHITE, 1.0, random.Random(0))
    quiet = moves.index(chess.Move.from_uci("a1a2"))        # does nothing about the rook on h1
    assert result.risks[quiet] == pytest.approx(6 / 9)      # one state of four, counted six times
    assert result.values[quiet] == pytest.approx(-6 / 9)    # and worth nothing where it is safe
    assert result.move.uci() in ("e1d2", "e1e2", "e1f2")    # so the king steps out of the line


def test_weigh_counts_states_with_our_king_attacked_more() -> None:
    from fow.obscuro.stockfish_search import weigh
    # One state in five has our king attacked; there every move but the second loses it.
    found = evidence([True, False, False, False, False],
                     [[1, 0], [0, 0], [0, 0], [0, 0], [0, 0]], [0, 1, 2, 3, 4],
                     [[-1.0, -0.5], [0.4, 0.0], [0.4, 0.0], [0.4, 0.0], [0.4, 0.0]])
    plain, risk = weigh(found, attacked_weight=1.0)
    assert risk[0] == pytest.approx(0.2) and plain[0] > plain[1]      # 0.12 against -0.10
    weighted, risk = weigh(found)  # the default weight for attacked states, 6
    assert risk[0] == pytest.approx(6 / 10)
    assert weighted[0] == pytest.approx(-0.6 + 0.4 * 0.4)
    assert weighted[1] == pytest.approx((6 * -0.5 + 4 * 0.0) / 10)    # that state counts for six
    assert weighted[1] > weighted[0]                                  # now the safe move wins
