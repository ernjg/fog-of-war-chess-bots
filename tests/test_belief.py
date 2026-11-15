"""The belief set always contains the true position (Proposition 1) when the cap is not hit."""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from fow.obscuro.belief import Belief, fit_to_view, project, state_key  # noqa: E402
from fow.obscuro.rules import side_to_move_wins  # noqa: E402
from referee import FowBoard, fow_moves, observation  # noqa: E402


def random_game(seed: int, plies: int):
    """Yield (board after the ply, mover, move) for a random game that avoids losing at once."""
    rng = random.Random(seed)
    board = FowBoard()
    for _ in range(plies):
        safe = [move for move in fow_moves(board) if not _loses_immediately(board, move)]
        if not safe:
            return
        move = rng.choice(safe)
        mover = board.turn
        board.push(move)
        yield board, mover, move


def _loses_immediately(board: FowBoard, move: chess.Move) -> bool:
    board.push(move)
    try:
        return side_to_move_wins(board)
    finally:
        board.pop()


@pytest.mark.parametrize("side", [chess.WHITE, chess.BLACK])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_true_state_stays_in_belief(side: chess.Color, seed: int) -> None:
    belief = Belief(side, max_states=10**6)
    belief.observe(observation(FowBoard(), side))
    for board, mover, move in random_game(seed, plies=24):
        belief.observe(observation(board, side), own_move=move if mover == side else None)
        assert state_key(board) in {state_key(state) for state in belief.states}
    assert belief.repairs == 0


def test_capped_belief_never_empties_and_agrees_with_view() -> None:
    side = chess.WHITE
    belief = Belief(side, max_states=1, rng=random.Random(0))
    belief.observe(observation(FowBoard(), side))
    for board, mover, move in random_game(3, plies=40):
        obs = observation(board, side)
        belief.observe(obs, own_move=move if mover == side else None)
        assert belief.states
        for state in belief.states:
            for square, char in enumerate(obs):
                if char != "?":
                    piece = state.piece_at(square)
                    assert (piece.symbol() if piece else "-") == char


def test_project_writes_observation_and_keeps_one_king() -> None:
    board = FowBoard()
    obs = observation(board, chess.WHITE)
    fixed = project(FowBoard(None), obs, chess.WHITE, chess.WHITE)
    assert all(fixed.piece_at(sq) is not None for sq in range(16))
    assert len(fixed.pieces(chess.KING, chess.BLACK)) == 1


def test_exact_flag_is_kept_while_nothing_is_dropped() -> None:
    belief = Belief(chess.WHITE, max_states=10**6)
    belief.observe(observation(FowBoard(), chess.WHITE))
    for board, mover, move in random_game(1, plies=16):
        belief.observe(observation(board, chess.WHITE), own_move=move if mover == chess.WHITE else None)
    assert belief.exact and belief.repairs == 0


@pytest.mark.parametrize("side", [chess.WHITE, chess.BLACK])
@pytest.mark.parametrize("seed", [0, 4])
def test_sampled_belief_stays_wide_and_fits_the_view(side: chess.Color, seed: int) -> None:
    """With a cap far below the number of consistent positions the true one is soon lost.
    The sample must then stay at the cap's size where it can, and every state in it must
    produce exactly what we see, be distinct, and leave nobody's king to be taken."""
    from fow.obscuro import belief as belief_module
    cap = 40
    belief = Belief(side, max_states=cap, rng=random.Random(seed))
    belief.observe(observation(FowBoard(), side))
    thin = sampled = misfit = 0
    for board, mover, move in random_game(seed, plies=60):
        obs = observation(board, side)
        belief.observe(obs, own_move=move if mover == side else None)
        assert belief.states and len(belief) <= cap
        assert len({state_key(state) for state in belief.states}) == len(belief)
        fits = [observation(state, side) == obs and not side_to_move_wins(state)
                for state in belief.states]
        for state in belief.states:
            assert state.turn == board.turn
            for square, char in enumerate(obs):  # at the least, what we see is there
                if char != "?":
                    piece = state.piece_at(square)
                    assert (piece.symbol() if piece else "-") == char
        if belief.repairs == 0:
            assert all(fits)  # only a repair can leave a state that implies another view
        assert all(fits) or not any(fits)  # and then only when no fitting state was found
        if not belief.exact:
            sampled += 1
            thin += len(belief) < min(cap, belief_module.MIN_POOL)
            misfit += not all(fits)
    assert not belief.exact and sampled > 20
    assert thin <= sampled // 4    # topped up nearly always (not when too little is hidden)
    assert misfit <= sampled // 10  # and nearly always with states that fit the view exactly


def test_replenish_leaves_an_exact_belief_alone() -> None:
    belief = Belief(chess.WHITE, max_states=10**6)
    obs = observation(FowBoard(), chess.WHITE)
    belief.observe(obs)
    belief.replenish(obs)
    assert len(belief) == 1  # the starting position is known; inventing others would be wrong
    belief.exact = False     # as after the cap or a repair
    belief.replenish(obs)
    assert all(observation(state, chess.WHITE) == obs for state in belief.states)
    assert len({state_key(state) for state in belief.states}) == len(belief) > 1


def test_walk_in_fog_only_moves_unseen_opponent_pieces() -> None:
    board = FowBoard("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    obs = observation(board, chess.WHITE)
    hidden = sum(chess.BB_SQUARES[sq] for sq, char in enumerate(obs) if char == "?")
    belief = Belief(chess.WHITE, rng=random.Random(3))
    for _ in range(200):
        walked = board.copy(stack=False)
        if not belief._walk_in_fog(walked, hidden):
            continue
        assert walked.turn == board.turn
        assert walked.occupied_co[chess.WHITE] == board.occupied_co[chess.WHITE]
        assert chess.popcount(walked.occupied_co[chess.BLACK]) == chess.popcount(board.occupied_co[chess.BLACK])
        visible = ~hidden & chess.BB_ALL
        assert walked.occupied & visible == board.occupied & visible  # nothing we see changed
        assert walked.castling_rights == walked.clean_castling_rights()


def test_fit_to_view_applies_the_two_pawn_rules() -> None:
    """Ahead of our e5 pawn we see nothing, so something stands on e6. Our d4 pawn sees no
    capture on c5, so nothing stands there. A guess that says otherwise is corrected."""
    truth = FowBoard("4k3/8/4n3/4P3/3P4/8/8/4K3 w - - 0 1")
    obs = observation(truth, chess.WHITE)
    assert obs[chess.E6] == "?" and obs[chess.C5] == "?" and obs[chess.D5] == "-"
    guess = FowBoard("4k3/8/8/2n1P3/3P4/8/8/4K3 w - - 0 1")  # the knight on c5: we would see it
    assert observation(guess, chess.WHITE) != obs
    fixed = fit_to_view(project(guess, obs, chess.WHITE, chess.WHITE), obs, chess.WHITE, random.Random(0))
    assert fixed.piece_at(chess.E6) == chess.Piece(chess.KNIGHT, chess.BLACK)
    assert fixed.piece_at(chess.C5) is None
    assert observation(fixed, chess.WHITE) == obs

    no_spare_piece = FowBoard("4k3/8/8/4P3/3P4/8/8/4K3 w - - 0 1")  # nothing to put on e6
    fixed = fit_to_view(project(no_spare_piece, obs, chess.WHITE, chess.WHITE), obs, chess.WHITE,
                        random.Random(0))
    assert fixed.piece_at(chess.E6) == chess.Piece(chess.PAWN, chess.BLACK)  # so one is assumed
    assert observation(fixed, chess.WHITE) == obs


@pytest.mark.parametrize("truth_fen, guess_fen, side, blocked, banned", [
    # The double step: e3 is seen empty and e4 is not seen, so e4 is what blocks the pawn.
    ("4k3/8/8/8/4n3/8/4P3/4K3 w - - 0 1", "4k3/8/8/8/5n2/8/4P3/4K3 w - - 0 1",
     chess.WHITE, chess.E4, None),
    # The same for Black, whose pawns start on the seventh rank and move down the board.
    ("4k3/4p3/8/4N3/8/8/8/4K3 b - - 0 1", "4k3/4p3/8/5N2/8/8/8/4K3 b - - 0 1",
     chess.BLACK, chess.E5, None),
    # Black's single step and capture rules: something stands on e4, nothing on d4.
    ("4k3/8/8/4p3/4N3/8/8/4K3 b - - 0 1", "4k3/8/8/4p3/3N4/8/8/4K3 b - - 0 1",
     chess.BLACK, chess.E4, chess.D4),
])
def test_fit_to_view_knows_the_double_step_and_both_colours(truth_fen, guess_fen, side, blocked,
                                                            banned) -> None:
    truth = FowBoard(truth_fen)
    obs = observation(truth, side)
    assert obs[blocked] == "?"
    guess = FowBoard(guess_fen)
    assert observation(guess, side) != obs  # the guess implies another view
    fixed = fit_to_view(project(guess, obs, side, side), obs, side, random.Random(0))
    assert fixed.piece_at(blocked) is not None and fixed.piece_at(blocked).color != side
    if banned is not None:
        assert fixed.piece_at(banned) is None
    assert observation(fixed, side) == obs


def test_fit_to_view_never_loses_the_king() -> None:
    """Every unseen square is taken or attacked by our pawn, and the guessed king stands
    on the attacked one: there is nowhere to move it. It stays, rather than vanish."""
    truth = FowBoard("7k/5P2/2Q3B1/5N2/8/6Q1/3K4/R7 w - - 0 1")
    obs = observation(truth, chess.WHITE)
    guess = FowBoard("3r2kr/5P2/2Q3B1/5N2/1n6/6Q1/1n1K4/R7 w - - 0 1")
    assert obs[chess.G8] == "?" and guess.king(chess.BLACK) == chess.G8
    belief = sampled_belief(chess.WHITE, [guess])
    belief.repair(obs, chess.WHITE)
    assert all(state.king(chess.BLACK) is not None for state in belief.states)
    assert all(len(state.pieces(chess.KING, chess.BLACK)) == 1 for state in belief.states)


def test_repaired_states_fit_the_view_in_most_cases() -> None:
    """A projected guess is one game's board under another game's observation. After the
    pawn rules are applied it should usually produce exactly that observation."""
    rng = random.Random(8)
    boards = [board.copy(stack=False) for seed in range(6) for board, _, _ in random_game(seed, plies=50)]
    fitted = plain = total = 0
    for _ in range(400):
        guess, truth = rng.choice(boards), rng.choice(boards)
        side = truth.turn
        obs = observation(truth, side)
        projected = project(guess, obs, side, side)
        plain += observation(projected, side) == obs
        fixed = fit_to_view(projected, obs, side, rng)
        assert len(fixed.pieces(chess.KING, not side)) == 1
        for square, char in enumerate(obs):  # what we see is never disturbed
            if char != "?":
                piece = fixed.piece_at(square)
                assert (piece.symbol() if piece else "-") == char
        fitted += observation(fixed, side) == obs
        total += 1
    assert fitted > plain and fitted >= 0.9 * total, (plain, fitted, total)


def sampled_belief(side: chess.Color, states: list[FowBoard], seed: int = 0) -> Belief:
    """A belief that has already lost its claim to be exact, as after the cap or a repair."""
    belief = Belief(side, rng=random.Random(seed))
    belief.states = states
    belief.exact = False
    belief._started = True
    return belief


def test_replenish_tops_up_from_the_states_that_fit_and_drops_the_rest(monkeypatch) -> None:
    """States left by a repair that imply another view are not counted towards the size
    wanted, and are gone as soon as one state fits."""
    from fow.obscuro import belief as belief_module
    monkeypatch.setattr(belief_module, "REPLENISH_SECONDS", 30.0)  # time is not what is tested
    truth = FowBoard("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    obs = observation(truth, chess.WHITE)
    strangers = [board.copy(stack=False) for board, _, _ in random_game(11, plies=160)
                 if board.turn == chess.WHITE and observation(board, chess.WHITE) != obs]
    assert len(strangers) >= 60
    belief = sampled_belief(chess.WHITE, [truth.copy(stack=False)] + strangers * 3)
    assert len(belief) > 128  # more than enough states, but only one of them fits
    belief._unchecked = True
    belief.replenish(obs)
    assert 1 < len(belief) <= 128
    assert all(observation(state, chess.WHITE) == obs and not side_to_move_wins(state)
               for state in belief.states)
    assert len({state_key(state) for state in belief.states}) == len(belief)
    assert state_key(truth) in {state_key(state) for state in belief.states}

    # When nothing fits, the states are left as they are rather than thrown away.
    belief = sampled_belief(chess.WHITE, [board.copy(stack=False) for board in strangers[:5]])
    belief._unchecked = True
    before = [state_key(state) for state in belief.states]
    belief.replenish(obs)
    assert [state_key(state) for state in belief.states] == before


class SteppingClock:
    """Stands in for the time module: every look at the clock moves it on by ``step``."""

    def __init__(self, step: float):
        self.now, self.step = 0.0, step

    def monotonic(self) -> float:
        self.now += self.step
        return self.now


def test_replenish_checks_repaired_states_only_as_far_as_its_time_goes(monkeypatch) -> None:
    from fow.obscuro import belief as belief_module
    truth = FowBoard("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    obs = observation(truth, chess.WHITE)
    grower = sampled_belief(chess.WHITE, [truth.copy(stack=False)], seed=2)
    monkeypatch.setattr(belief_module, "MIN_POOL", 600)
    monkeypatch.setattr(belief_module, "MAX_MISSES", 10**6)
    monkeypatch.setattr(belief_module, "REPLENISH_SECONDS", 30.0)
    grower.replenish(obs)
    fitting = grower.states
    assert len(fitting) == 600  # distinct states that all produce this view

    # The clock is looked at once to set the deadline and once per state checked, so with
    # 0.1 s allowed and 1 ms per look, 99 states get their check and the rest are dropped.
    monkeypatch.setattr(belief_module, "MIN_POOL", 50)
    monkeypatch.setattr(belief_module, "REPLENISH_SECONDS", 0.1)
    monkeypatch.setattr(belief_module, "time", SteppingClock(0.001))
    belief = sampled_belief(chess.WHITE, list(fitting))
    belief._unchecked = True  # as a repair leaves them
    belief.replenish(obs)
    assert len(belief) == 99
    assert all(observation(state, chess.WHITE) == obs for state in belief.states)


def test_replenish_stops_at_once_when_nothing_unseen_can_move(monkeypatch) -> None:
    """A lone king boxed in by squares we see has nowhere to go out of our sight. The
    top-up must give up after a few failed tries, not use up its time allowance."""
    from fow.obscuro import belief as belief_module
    truth = FowBoard("k7/7R/8/8/8/8/8/1R2K3 w - - 0 1")
    obs = observation(truth, chess.WHITE)
    assert obs[chess.A8] == "?" and all(obs[square] == "-" for square in (chess.A7, chess.B7, chess.B8))
    monkeypatch.setattr(belief_module, "REPLENISH_SECONDS", 60.0)
    belief = sampled_belief(chess.WHITE, [truth.copy(stack=False)])
    started = time.monotonic()
    belief.replenish(obs)
    assert time.monotonic() - started < 5.0
    assert [state_key(state) for state in belief.states] == [state_key(truth)]


def test_walk_in_fog_castles_with_the_rook_and_drops_the_rights(monkeypatch) -> None:
    from fow.obscuro import belief as belief_module
    monkeypatch.setattr(belief_module, "WALK_STEPS", (1,))  # one move per walk: no king walks to g8
    board = FowBoard("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    obs = observation(board, chess.WHITE)
    hidden = sum(chess.BB_SQUARES[square] for square, char in enumerate(obs) if char == "?")
    belief = Belief(chess.WHITE, rng=random.Random(5))
    castled = set()
    for _ in range(400):
        walked = board.copy(stack=False)
        if not belief._walk_in_fog(walked, hidden):
            continue
        king = walked.king(chess.BLACK)
        if king in (chess.G8, chess.C8):
            rook_to, rook_from = (chess.F8, chess.H8) if king == chess.G8 else (chess.D8, chess.A8)
            assert walked.piece_at(rook_to) == chess.Piece(chess.ROOK, chess.BLACK)
            assert walked.piece_at(rook_from) is None
            assert not walked.castling_rights & chess.BB_RANK_8  # black can no longer castle
            castled.add(king)
        assert walked.castling_rights == walked.clean_castling_rights()
        assert chess.popcount(walked.occupied_co[chess.BLACK]) == 11
        assert observation(walked, chess.WHITE) == obs  # all of it out of our sight
    assert castled == {chess.G8, chess.C8}


def test_walk_in_fog_leaves_the_square_behind_a_double_step_empty() -> None:
    """With en passant possible on d6, the pawn on d5 has just come from d7 in one move,
    so d7 is empty. Without it, the pieces around d7 do move there."""
    after_double_step = FowBoard("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3")
    obs = observation(after_double_step, chess.WHITE)
    hidden = sum(chess.BB_SQUARES[square] for square, char in enumerate(obs) if char == "?")
    assert obs[chess.D7] == "?" and obs[chess.D6] == "-"  # we see d6: the capture is on
    belief = Belief(chess.WHITE, rng=random.Random(9))
    onto_d7 = {True: 0, False: 0}
    for with_en_passant in (True, False):
        for _ in range(300):
            walked = after_double_step.copy(stack=False)
            if not with_en_passant:
                walked.ep_square = None
            belief._walk_in_fog(walked, hidden)
            onto_d7[with_en_passant] += walked.piece_at(chess.D7) is not None
            if with_en_passant:
                assert walked.ep_square == chess.D6  # the pawn is in our sight and stays put
    assert onto_d7[True] == 0 and onto_d7[False] > 20


def test_limit_cuts_the_set_and_marks_it_a_sample() -> None:
    belief = Belief(chess.WHITE, max_states=1500, rng=random.Random(4))
    belief.observe(observation(FowBoard(), chess.WHITE))
    for board, mover, move in random_game(4, plies=8):
        belief.observe(observation(board, chess.WHITE), own_move=move if mover == chess.WHITE else None)
    size = len(belief)
    assert belief.exact and size > 200
    belief.limit(size + 10)          # room to spare: nothing happens to the states
    assert belief.exact and len(belief) == size and belief.max_states == size + 10
    belief.limit(100)
    assert not belief.exact and len(belief) == 100 and belief.max_states == 100
    assert len({state_key(state) for state in belief.states}) == 100
    belief.limit(1500)               # the cap goes back up; what was dropped stays dropped
    assert not belief.exact and len(belief) == 100 and belief.max_states == 1500
