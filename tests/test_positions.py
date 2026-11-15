"""The compiled position-set helper (bots/obscuro/positions.cpp) against the referee and
against the Python belief. The helper is built here with the system's C++ compiler; the
tests are skipped where there is none."""
from __future__ import annotations

import random
import subprocess
import sys
import time
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fow  # noqa: E402,F401
import chess  # noqa: E402

from fow.obscuro import position_set  # noqa: E402
from fow.obscuro.belief import HEAD_SHARE, MIN_POOL, Belief, state_key  # noqa: E402
from fow.obscuro.opponent import KING_MISS, OTHER  # noqa: E402
from fow.obscuro.position_set import Helper, HelperError, PositionSet  # noqa: E402
from fow.obscuro.rules import side_to_move_wins  # noqa: E402
from referee import FowBoard, fow_moves, observation  # noqa: E402

def answers(helper: str, questions: list[str]) -> list[str]:
    out = subprocess.run([helper], input="\n".join(questions) + "\nquit\n", capture_output=True,
                         text=True, timeout=300)
    assert out.returncode == 0 and not out.stderr, out.stderr[:500]
    return out.stdout.splitlines()


def random_positions(seed: int, games: int, plies: int) -> list[FowBoard]:
    """Positions from games played four ways, so that every kind of move turns up: at
    random (kings get taken), mostly captures and pawn moves (promotions, en passant),
    kings kept alive (long games), and castling whenever it is possible."""
    rng = random.Random(seed)
    found = []
    for game in range(games):
        board = FowBoard()
        for _ in range(plies):
            moves = fow_moves(board)
            if not moves or (board.king(chess.WHITE) is None and board.king(chess.BLACK) is None):
                break
            style = game % 4
            if style == 1:
                loud = [m for m in moves if board.is_capture(m) or board.piece_type_at(m.from_square) == chess.PAWN]
                move = rng.choice(loud if loud and rng.random() < 0.7 else moves)
            elif style == 2:
                move = rng.choice([m for m in moves if board.piece_type_at(m.to_square) != chess.KING] or moves)
            elif style == 3:
                castles = [m for m in moves if board.is_castling(m)]
                move = rng.choice(castles if castles and rng.random() < 0.5 else moves)
            else:
                move = rng.choice(moves)
            board.push(move)
            found.append(board.copy(stack=False))
    return found


HANDMADE = [
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",          # all four castlings
    "r3k2r/8/8/8/8/8/6q1/R3K2R w KQkq - 0 1",        # castling out of and through attack is allowed
    "4k3/8/8/8/8/8/8/R3K2R w K - 0 1",               # a right for one side only
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",   # en passant available
    "rnbqkbnr/ppp1pppp/8/8/3pP3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 2",    # and for Black
    "n1n5/PPPk4/8/8/8/8/4Kppp/5N1N b - - 0 1",       # promotions, with and without capture
    "r6k/1P6/8/8/8/8/8/K7 w - - 0 1",                # promotion by capture in a corner
    "4k3/8/8/8/8/8/8/4KQ2 w - - 0 1",
    "8/8/8/8/8/8/8/Kk6 w - - 0 1",                   # kings side by side: either can take the other
    "8/8/8/3k4/8/8/8/8 w - - 0 1",                   # no white king
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
]


def test_selftest_passes(helper) -> None:
    out = subprocess.run([helper, "selftest"], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.startswith("selftest ok"), out.stdout


def test_rules_match_the_referee(helper) -> None:
    """Position by position: the moves, in the referee's order; whether the side to move
    can take the king; what each side sees; and the position after every move."""
    positions = random_positions(1, games=40, plies=80) + [FowBoard(fen) for fen in HANDMADE]
    questions, expected = [], []
    for board in positions:
        fen = board.fen(en_passant="fen")
        moves = fow_moves(board)
        questions.append(f"moves {fen}")
        expected.append(" ".join(["moves", str(len(moves)), *(move.uci() for move in moves)]))
        questions.append(f"wins {fen}")
        expected.append(f"wins {int(side_to_move_wins(board))}")
        for side, letter in ((chess.WHITE, "w"), (chess.BLACK, "b")):
            questions.append(f"obs {fen} {letter}")
            expected.append("obs " + observation(board, side))
        for move in moves:
            after = board.copy(stack=False)
            after.push(move)
            questions.append(f"push {fen} {move.uci()}")
            expected.append("fen " + after.fen(en_passant="fen"))
    found = answers(helper, questions)
    assert len(found) == len(expected)
    wrong = [(q, e, f) for q, e, f in zip(questions, expected, found, strict=True) if e != f]
    assert not wrong, wrong[:3]
    kinds = [m for board in positions for m in fow_moves(board)]
    assert len(positions) > 2000 and len(questions) > 50_000
    assert any(m.promotion for m in kinds)
    assert any(board.is_castling(m) for board in positions for m in fow_moves(board))
    assert any(board.is_en_passant(m) for board in positions for m in fow_moves(board))
    assert any(board.king(chess.WHITE) is None or board.king(chess.BLACK) is None for board in positions)


def test_bad_input_gets_an_error_and_the_helper_carries_on(helper) -> None:
    found = answers(helper, ["nonsense", "moves not a fen", "own e2e9 " + "?" * 64, "init short",
                             "commit 0 0 0", "moves rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"])
    assert all(line.startswith("err") for line in found[:5]) and found[5].startswith("moves 20 ")


def hash_odds(board: chess.Board, n_moves: int) -> dict[str, float]:
    """Made-up odds for every move of the side to move: fixed, uneven, summing to 1; and
    what opponent.OpponentPolicy says of a side that could have taken the king."""
    if side_to_move_wins(board):
        return {OTHER: KING_MISS / max(n_moves, 1)}
    raw = {move.uci(): 1 + zlib.crc32((board.board_fen() + move.uci()).encode()) % 7 for move in fow_moves(board)}
    total = sum(raw.values())
    return {**{uci: value / total for uci, value in raw.items()}, OTHER: 0.0}


def hash_policy(boards, counts):
    return [hash_odds(board, n) for board, n in zip(boards, counts, strict=True)]


def everything(position_set_: PositionSet) -> dict:
    """Every state the helper holds, with its weight."""
    _, rows = position_set_.helper.ask(f"dump {10 ** 9}", time.monotonic() + 60)
    found = {}
    for row in rows:
        _, weight, fen = row.split(" ", 2)
        key = state_key(FowBoard(fen))
        assert key not in found, "the helper holds a state twice"
        found[key] = float(weight)
    return found


@pytest.mark.parametrize("policy", [None, hash_policy], ids=["equal odds", "with a policy"])
def test_the_set_is_the_python_beliefs_set(helper, policy, monkeypatch) -> None:
    """Games seen from one side, the set kept twice: by belief.Belief without a cap, and by
    the helper. After every ply they hold the same positions, with the same weights."""
    monkeypatch.setattr(position_set, "ASK_STATES", 10 ** 9)  # ask the policy about every state, as Belief does
    rng = random.Random(7)
    compared = largest = 0
    for game in range(8):
        side = chess.WHITE if game % 2 == 0 else chess.BLACK
        board = FowBoard()
        belief = Belief(side, 10 ** 9, random.Random(game))
        full = PositionSet(side, [helper], 10 ** 9, random.Random(game))
        full.allowance = 600.0
        try:
            for ply in range(41):
                own = None
                if ply > 0:
                    safe = []
                    for move in fow_moves(board):  # nobody leaves a king to be taken, as in a game that goes on
                        board.push(move)
                        if not side_to_move_wins(board):
                            safe.append(move)
                        board.pop()
                    if not safe:
                        break
                    quiet = [m for m in safe if not board.is_capture(m)]
                    move = rng.choice(quiet if quiet and rng.random() < 0.8 else safe)
                    own = move if board.turn == side else None
                    board.push(move)
                obs = observation(board, side)
                use = policy if own is None else None
                belief.observe(obs, own_move=own, policy=use)
                full.observe(obs, own_move=own, policy=use)
                assert full.fallback is None, full.failure
                want = {state_key(state): weight for state, weight in zip(belief.states, belief.weights, strict=True)}
                got = everything(full)
                assert got.keys() == want.keys(), (game, ply, len(got), len(want))
                assert state_key(board) in got                       # the true position is never lost
                assert (len(full), full.exact, full.weighted) == (len(belief), belief.exact, belief.weighted)
                assert max(abs(got[key] - want[key]) for key in want) < 1e-9
                assert full.effective_size() == pytest.approx(belief.effective_size(), rel=1e-3, abs=1e-3)
                assert full.ep_squares() == belief.ep_squares()
                # What Python sees of it: all of it while small, else 256 draws by weight.
                if len(want) <= position_set.SAMPLE_STATES:
                    assert {state_key(s): w for s, w in zip(full.states, full.weights, strict=True)} == got
                else:
                    assert sum(full.weights) == position_set.SAMPLE_STATES or not full.weighted
                    assert all(state_key(s) in got for s in full.states)
                compared += 1
                largest = max(largest, len(want))
                if len(want) > 1500:
                    break
        finally:
            full.close()
    assert compared > 60 and largest > 1500


def loaded(helper: str, states: list[FowBoard], weights: list[float], cap: int = 10 ** 6, seed: int = 3) -> Helper:
    process = Helper([helper])
    process.ask(f"new w {cap} {seed} {HEAD_SHARE!r}", time.monotonic() + 5)
    rows = [f"s {weight!r} {state.fen(en_passant='fen')}" for state, weight in zip(states, weights, strict=True)]
    process.ask("\n".join([f"load 1 1 {len(rows)}", *rows]), time.monotonic() + 30)
    return process


def distinct_positions(count: int) -> list[FowBoard]:
    found, seen = [], set()
    for board in random_positions(5, games=40, plies=60):
        if board.turn == chess.WHITE and state_key(board) not in seen:
            seen.add(state_key(board))
            found.append(board)
    assert len(found) >= count
    return found[:count]


def test_a_cut_keeps_the_heaviest_states_and_a_fair_share_of_the_rest(helper) -> None:
    """belief.Belief._cut, done by the helper: of 1,000 states cut to 200, the heaviest 150
    stay as they are and 50 of the other 850 are drawn, each then standing for 17."""
    states = distinct_positions(1000)
    weights = [1000.0 - index for index in range(1000)]
    process = loaded(helper, states, weights)
    try:
        header, _ = process.ask("limit 200", time.monotonic() + 5)
        assert "size=200 exact=0" in header
        _, rows = process.ask("dump 1000", time.monotonic() + 5)
        kept = [(float(row.split(" ", 2)[1]), state_key(FowBoard(row.split(" ", 2)[2]))) for row in rows]
        where = {state_key(state): index for index, state in enumerate(states)}
        head = int(HEAD_SHARE * 200)
        assert [where[key] for _, key in kept[:head]] == list(range(head))
        assert [weight for weight, _ in kept[:head]] == weights[:head]
        drawn = [where[key] for _, key in kept[head:]]
        assert min(drawn) >= head and len(set(drawn)) == 200 - head
        scale = (1000 - head) / (200 - head)
        assert [weight for weight, _ in kept[head:]] == pytest.approx([weights[index] * scale for index in drawn])
    finally:
        process.quit()
    # With equal weights the cut is a plain random sample.
    process = loaded(helper, states, [1.0] * 1000)
    try:
        process.ask("limit 200", time.monotonic() + 5)
        _, rows = process.ask("dump 1000", time.monotonic() + 5)
        picked = sorted(where[state_key(FowBoard(row.split(" ", 2)[2]))] for row in rows)
        assert len(set(picked)) == 200 and {float(row.split(" ", 2)[1]) for row in rows} == {1.0}
        assert 350 < sum(picked) / 200 < 650       # from all over, not the first 200
    finally:
        process.quit()


def test_a_sample_counts_each_state_for_its_share(helper) -> None:
    """stockfish_search.draw, done by the helper: 256 draws by weight, the heaviest first."""
    states = distinct_positions(500)
    weights = [1.0] * 500
    weights[7], weights[8] = 500.0, 250.0            # half and a quarter of 1,248 between them
    process = loaded(helper, states, weights)
    try:
        _, rows = process.ask("sample 256", time.monotonic() + 5)
        drawn = [(float(row.split(" ", 2)[1]), state_key(FowBoard(row.split(" ", 2)[2]))) for row in rows]
        assert sum(count for count, _ in drawn) == 256
        assert [key for _, key in drawn[:2]] == [state_key(states[7]), state_key(states[8])]
        assert drawn[0][0] == pytest.approx(256 * 500 / 1248, abs=1) and drawn[1][0] == pytest.approx(256 * 250 / 1248, abs=1)
        assert len(drawn) < 120 and all(count == 1.0 for count, _ in drawn[2:])
        assert len({key for _, key in drawn}) == len(drawn)
        header, _ = process.ask("find " + states[7].fen(en_passant="fen"), time.monotonic() + 5)
        assert header.split() == ["found", "500", "1248"]
        header, _ = process.ask("find " + FowBoard().fen(en_passant="fen"), time.monotonic() + 5)
        assert header.startswith("missing")
    finally:
        process.quit()
    process = loaded(helper, states, [2.0] * 500)   # equal weights: 256 different states, once each
    try:
        _, rows = process.ask("sample 256", time.monotonic() + 5)
        assert len({row.split(" ", 2)[2] for row in rows}) == 256 and {row.split(" ", 2)[1] for row in rows} == {"1"}
    finally:
        process.quit()


def hidden_game(full: PositionSet, plies: int) -> FowBoard:
    """White moves a knight out and back and sees nothing; Black plays quiet moves out of
    sight. The set grows with every move of Black's."""
    rng = random.Random(5)
    board = FowBoard()
    full.observe(observation(board, chess.WHITE))
    for index in range(plies):
        move = chess.Move.from_uci(("g1f3", "f3g1")[index % 2])
        board.push(move)
        full.observe(observation(board, chess.WHITE), own_move=move)
        replies = []
        for reply in fow_moves(board):
            board.push(reply)
            if not side_to_move_wins(board) and observation(board, chess.WHITE).count("?") >= 30:
                replies.append(reply)
            board.pop()
        board.push(rng.choice([m for m in replies if not board.is_capture(m)]))
        full.observe(observation(board, chess.WHITE))
    return board


def test_the_helper_stops_at_its_time_and_says_the_set_is_no_longer_complete(helper) -> None:
    full = PositionSet(chess.WHITE, [helper], 10 ** 6, random.Random(1))
    try:
        full.allowance = 60.0
        board = hidden_game(full, 3)
        assert full.exact and len(full) > 2000
        before = len(full)
        move = chess.Move.from_uci("f3g1")
        board.push(move)
        full.observe(observation(board, chess.WHITE), own_move=move)
        board.push(next(m for m in fow_moves(board) if m.uci() == "a7a6" or m.uci() == "h7h6"))
        header, rows = full.helper.ask(f"opp {observation(board, chess.WHITE)} 0.001 0", time.monotonic() + 10)
        assert rows == []
        fields = full._ok("commit 0 0 0")
        assert 0 < int(fields["expanded"]) < before     # it did not get through them all
        assert not full.exact and 0 < len(full)
    finally:
        full.close()


def test_the_cap_is_kept_and_a_cut_set_is_only_a_sample(helper) -> None:
    full = PositionSet(chess.WHITE, [helper], 300, random.Random(1))
    try:
        full.allowance = 60.0
        hidden_game(full, 4)
        assert len(full) == 300 and not full.exact
        assert len(full.states) == position_set.SAMPLE_STATES   # a sample of the 300
        full.limit(200)
        assert len(full) == 200 and full.max_states == 200
    finally:
        full.close()


def test_a_set_emptied_by_an_observation_is_rebuilt_and_topped_up(helper) -> None:
    """With a cap of four the true position is soon gone, and then an observation fits
    none of the states. The set is rebuilt from what Python has of it (Belief.repair) and
    widened again (Belief.replenish), as the Python belief does for itself."""
    rng = random.Random(11)
    full = PositionSet(chess.WHITE, [helper], 4, random.Random(2))
    board = FowBoard()
    try:
        full.allowance = 60.0
        full.observe(observation(board, chess.WHITE))
        for _ in range(40):
            safe = []
            for move in fow_moves(board):
                board.push(move)
                if not side_to_move_wins(board):
                    safe.append(move)
                board.pop()
            if not safe:
                break
            move = rng.choice(safe)
            ours = board.turn == chess.WHITE
            board.push(move)
            obs = observation(board, chess.WHITE)
            full.observe(obs, own_move=move if ours else None)
            assert full.fallback is None, full.failure
            assert 1 <= len(full) <= max(4, MIN_POOL) and len(full.states) == len(full)
            if full.repairs and not ours:
                break
        assert full.repairs >= 1 and not full.exact
        fitting = [state for state in full.states if observation(state, chess.WHITE) == obs]
        assert fitting, "after a rebuild some state should produce what we see"
    finally:
        full.close()


def test_the_policy_is_asked_about_the_heaviest_states_only(helper, monkeypatch) -> None:
    monkeypatch.setattr(position_set, "ASK_STATES", 5)
    asked = []

    def policy(boards, counts):
        asked.append([board.fen() for board in boards])
        return hash_policy(boards, counts)

    full = PositionSet(chess.WHITE, [helper], 10 ** 6, random.Random(1))
    try:
        full.allowance = 60.0
        board = FowBoard()
        full.observe(observation(board, chess.WHITE))
        rng = random.Random(3)
        for index in range(3):
            move = chess.Move.from_uci(("g1f3", "f3g1")[index % 2])
            board.push(move)
            full.observe(observation(board, chess.WHITE), own_move=move)
            board.push(rng.choice([m for m in fow_moves(board) if not board.is_capture(m)]))
            weights_before = dict(zip((state.fen() for state in full.states), full.weights, strict=True))
            full.observe(observation(board, chess.WHITE), policy=policy)
            assert full.weighted and len(asked[-1]) <= 5 and full.asked == len(asked[-1])
            if len(weights_before) > 5 and len(weights_before) <= position_set.SAMPLE_STATES:
                # They are the heaviest of the states there were (ties aside).
                lightest_asked = min(weights_before[fen] for fen in asked[-1])
                assert sum(weight > lightest_asked for weight in weights_before.values()) < 5
    finally:
        full.close()


def test_a_policy_that_fails_is_no_policy(helper) -> None:
    def broken(boards, counts):
        raise RuntimeError("no engines")

    full = PositionSet(chess.WHITE, [helper], 10 ** 6, random.Random(1))
    try:
        board = FowBoard()
        full.observe(observation(board, chess.WHITE))
        board.push_uci("g1f3")
        full.observe(observation(board, chess.WHITE), own_move=chess.Move.from_uci("g1f3"))
        board.push_uci("a7a6")   # out of sight; the knight on f3 would see a pawn on e5 or g5
        full.observe(observation(board, chess.WHITE), policy=broken)
        assert full.fallback is None and not full.weighted and len(full) == 18
        assert set(full.weights) == {1.0}
    finally:
        full.close()


def test_losing_the_helper_carries_on_in_python(helper) -> None:
    """The helper is killed in mid-game. The set goes on as a Python belief started from
    what Python last saw, and since that was all of it, nothing is lost."""
    rng = random.Random(4)
    full = PositionSet(chess.WHITE, [helper], 10 ** 6, random.Random(1))
    twin = Belief(chess.WHITE, 10 ** 6, random.Random(1))
    board = FowBoard()
    try:
        for ply in range(13):
            own = None
            if ply > 0:
                move = rng.choice([m for m in fow_moves(board) if not board.is_capture(m)])
                own = move if board.turn == chess.WHITE else None
                board.push(move)
            if ply == 6:
                full.helper.proc.kill()
                full.helper.proc.wait(timeout=5)
            obs = observation(board, chess.WHITE)
            full.observe(obs, own_move=own)
            twin.observe(obs, own_move=own)
            assert (full.fallback is not None) == (ply >= 6)
            if len(twin) <= position_set.SAMPLE_STATES or ply >= 6:
                assert {state_key(s) for s in full.states} == {state_key(s) for s in twin.states}
                assert len(full) == len(twin) and full.exact == twin.exact
        assert "exited" in full.failure or "gone" in full.failure or "failed" in full.failure
        size = len(full)
        assert size > 1
        full.limit(size - 1)     # the cap still works, on the Python belief now
        assert len(full) == size - 1 and full.max_states == size - 1 and not full.exact
        full.repair(obs, chess.WHITE)
        assert full.states
    finally:
        full.close()


def test_a_helper_that_does_not_answer_is_given_up_in_time(tmp_path, monkeypatch) -> None:
    """A stand-in that reads and never answers: the set is not created; and one that
    answers the first command only is given up at the next, within the time allowed."""
    mute = tmp_path / "mute.py"
    mute.write_text("import sys\nfor line in sys.stdin:\n    pass\n")
    monkeypatch.setattr(position_set, "START_SECONDS", 0.3)
    monkeypatch.setattr(position_set, "ANSWER_SECONDS", 0.3)
    began = time.monotonic()
    with pytest.raises(HelperError):
        PositionSet(chess.WHITE, [sys.executable, str(mute)], 1000, random.Random(1))
    assert time.monotonic() - began < 2.0

    once = tmp_path / "once.py"
    once.write_text("import sys\nprint('ok size=1 exact=1 weighted=0 ess=1.000 ep=0 parents=0 expanded=0 kids=0 ms=0.00', flush=True)\n"
                    "for line in sys.stdin:\n    pass\n")
    full = PositionSet(chess.WHITE, [sys.executable, str(once)], 1000, random.Random(1))
    try:
        began = time.monotonic()
        full.observe(observation(FowBoard(), chess.WHITE))
        assert time.monotonic() - began < 2.0
        assert full.fallback is not None and "in time" in full.failure and len(full) == 1
    finally:
        full.close()

    garbage = tmp_path / "garbage.py"
    garbage.write_text("import sys\nfor line in sys.stdin:\n    print('what?', flush=True)\n")
    with pytest.raises(HelperError):
        PositionSet(chess.WHITE, [sys.executable, str(garbage)], 1000, random.Random(1))
