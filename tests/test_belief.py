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


def test_a_repair_does_not_count_a_piece_twice(monkeypatch) -> None:
    """The black queen comes into view on h4. Every state had guessed it on d8, out of
    sight behind the bishop, so none has a successor with it on h4 and the set is rebuilt.
    The guess on d8 must go: with two queens and eight pawns no state would be a position
    Stockfish takes, and its search would be off until the material changed."""
    from fow.obscuro.stockfish_search import engine_accepts
    guess = FowBoard("rnbqk2r/ppppbppp/5n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1")
    truth = FowBoard("rnbqkbnr/ppp2pp1/3p3p/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1")
    before = observation(truth, chess.WHITE)
    assert observation(guess, chess.WHITE) == before  # the two cannot be told apart
    belief = sampled_belief(chess.WHITE, [guess.copy(stack=False)])
    truth.push_uci("d8h4")
    obs = observation(truth, chess.WHITE)
    assert obs[chess.H4] == "q" and obs[chess.D8] == "?"
    belief.observe(obs)
    assert belief.repairs == 1 and len(belief) > 1
    for state in belief.states:
        assert len(state.pieces(chess.QUEEN, chess.BLACK)) == 1
        assert state.piece_at(chess.H4) == chess.Piece(chess.QUEEN, chess.BLACK)
        assert len(state.pieces(chess.PAWN, chess.BLACK)) == 8
        assert observation(state, chess.WHITE) == obs
        assert engine_accepts(state)


def test_a_repair_keeps_the_material_possible() -> None:
    """Whatever is projected onto whatever: no more opponent pieces of a kind than the old
    state had, unless we see them all, and never more than a game can produce."""
    from fow.obscuro.stockfish_search import engine_accepts
    rng = random.Random(12)
    boards = [board.copy(stack=False) for seed in range(8) for board, _, _ in random_game(seed, plies=60)]
    possible = 0
    for _ in range(500):
        guess, truth = rng.choice(boards), rng.choice(boards)
        side = truth.turn
        obs = observation(truth, side)
        fixed = project(guess, obs, side, side)
        for kind in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            now = fixed.pieces(kind, not side)
            seen = [square for square in now if obs[square] != "?"]
            assert len(now) <= max(len(guess.pieces(kind, not side)), len(seen))
        possible += engine_accepts(fit_to_view(fixed, obs, side, rng))
    assert possible >= 490  # the rest are states where a king could be taken


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


# ---------------------------------------------------------------------------------------
# Weights.

def test_without_a_policy_every_state_weighs_the_same() -> None:
    belief = Belief(chess.WHITE, max_states=60, rng=random.Random(1))
    belief.observe(observation(FowBoard(), chess.WHITE))
    for board, mover, move in random_game(1, plies=30):
        belief.observe(observation(board, chess.WHITE), own_move=move if mover == chess.WHITE else None)
        assert len(belief.weights) == len(belief.states)
        assert set(belief.weights) == {1.0}
        assert belief.effective_size() == pytest.approx(len(belief))
    assert not belief.weighted and not belief.exact


def likes(favourite: str, chance: float = 0.9):
    """A policy that gives ``favourite`` (a UCI move) most of the probability wherever the
    opponent can play it, and shares the rest among the other moves."""
    from fow.obscuro.opponent import OTHER

    def policy(boards, counts):
        tables = []
        for board, n_moves in zip(boards, counts, strict=True):
            if chess.Move.from_uci(favourite) in board.generate_pseudo_legal_moves():
                tables.append({favourite: chance, OTHER: (1 - chance) / (n_moves - 1)})
            else:
                tables.append(None)
        return tables

    return policy


def test_a_policy_makes_the_likely_move_weigh_more() -> None:
    """After 1. a3 we see nothing of Black's reply: all twenty are consistent. With a
    policy that expects ...e5, that position outweighs each of the others nine to one
    nineteenth; without one they weigh the same."""
    board = FowBoard()
    belief = Belief(chess.WHITE, rng=random.Random(0))
    belief.observe(observation(board, chess.WHITE))
    board.push_uci("a2a3")
    belief.observe(observation(board, chess.WHITE), own_move=chess.Move.from_uci("a2a3"))
    board.push_uci("g8f6")
    belief.observe(observation(board, chess.WHITE), policy=likes("e7e5"))
    assert len(belief) == 20 and belief.weighted
    by_fen = {state.board_fen(): weight for state, weight in zip(belief.states, belief.weights, strict=True)}
    after_e5 = FowBoard()
    after_e5.push_uci("a2a3")
    after_e5.push_uci("e7e5")
    assert by_fen[after_e5.board_fen()] == 1.0                      # the heaviest is the unit
    others = [weight for fen, weight in by_fen.items() if fen != after_e5.board_fen()]
    assert others == pytest.approx([(0.1 / 19) / 0.9] * 19)
    assert belief.effective_size() == pytest.approx(1.0, abs=0.3)   # as good as one state
    assert belief.exact                                             # weights drop nothing


def test_weights_follow_the_states_through_our_own_moves_and_add_up_over_transpositions() -> None:
    board = FowBoard()
    belief = Belief(chess.WHITE, rng=random.Random(0))
    belief.observe(observation(board, chess.WHITE))
    for ours, theirs in (("a2a3", "g8f6"), ("h2h3", "b8c6")):
        board.push_uci(ours)
        belief.observe(observation(board, chess.WHITE), own_move=chess.Move.from_uci(ours))
        board.push_uci(theirs)
        belief.observe(observation(board, chess.WHITE), policy=likes("g8f6", 0.5))
    # Both knights out is one position reached two ways: Nf6 then Nc6, or Nc6 then Nf6.
    # The knight on d5 is reached one way only, Nf6 then Nd5 (most other pairs of moves
    # can be played in either order, so they are no use as the comparison).
    weights = {state_key(state): weight for state, weight in zip(belief.states, belief.weights, strict=True)}
    assert max(weights.values()) == 1.0 and len(weights) == len(belief.states)
    after_nf6 = FowBoard()
    for uci in ("a2a3", "g8f6", "h2h3"):
        after_nf6.push_uci(uci)
    replies = len(list(fow_moves(after_nf6)))
    one_way = after_nf6.copy()
    one_way.push_uci("f6d5")
    two_ways = board
    # After the first move Nf6 weighs 1 and each other reply 1/19 of that. From Nf6 the
    # policy has no favourite (the knight has gone), so every reply has equal odds; from
    # Nc6 it gives Nf6 a half.
    by_nf6_first = 1.0 / replies
    by_nc6_first = (1.0 / 19) * 0.5
    assert weights[state_key(two_ways)] / weights[state_key(one_way)] == pytest.approx(
        (by_nf6_first + by_nc6_first) / by_nf6_first)


def _odds_by_hash(board, n_moves):
    """Made-up odds for every move of the side to move: fixed, uneven, summing to 1."""
    import zlib
    from fow.obscuro.opponent import OTHER
    raw = {move.uci(): 1 + zlib.crc32((board.board_fen() + move.uci()).encode()) % 7
           for move in fow_moves(board)}
    assert len(raw) == n_moves
    total = sum(raw.values())
    return {**{uci: value / total for uci, value in raw.items()}, OTHER: 0.0}


@pytest.mark.parametrize("side, line", [
    (chess.WHITE, ("e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5", "d2d4", "c7c6")),
    (chess.BLACK, ("g1f3", "a7a6", "d2d4", "h7h6", "c2c4")),   # we see nothing of White's moves
])
def test_the_weights_are_the_exact_probabilities_of_the_positions(side, line) -> None:
    """Against a count that does not share the belief's bookkeeping: every sequence of
    opponent moves that fits what we saw, each with the product of its moves' odds, added
    up by the position it ends in."""
    def policy(boards, counts):
        return [_odds_by_hash(board, n) for board, n in zip(boards, counts, strict=True)]

    board = FowBoard()
    belief = Belief(side, 100_000, rng=random.Random(0))
    belief.observe(observation(board, side))
    paths = [(FowBoard(), 1.0)]
    for uci in line:
        move = chess.Move.from_uci(uci)
        ours = board.turn == side
        board.push(move)
        seen = observation(board, side)
        belief.observe(seen, own_move=move if ours else None, policy=None if ours else policy)
        longer = []
        for position, chance in paths:
            replies = [move] if ours else list(fow_moves(position))
            odds = None if ours else _odds_by_hash(position, len(replies))
            for reply in replies:
                if reply not in fow_moves(position):
                    continue
                after = position.copy(stack=False)
                after.push(reply)
                if not side_to_move_wins(after) and observation(after, side) == seen:
                    longer.append((after, chance * (1.0 if ours else odds[reply.uci()])))
        paths = longer
    assert belief.exact and belief.weighted
    expected: dict = {}
    for position, chance in paths:
        expected[state_key(position)] = expected.get(state_key(position), 0.0) + chance
    assert len(paths) > len(expected) > 20           # transpositions among them
    top = max(expected.values())
    found = {state_key(state): weight for state, weight in zip(belief.states, belief.weights, strict=True)}
    assert found.keys() == expected.keys()
    for key, chance in expected.items():
        assert found[key] == pytest.approx(chance / top, rel=1e-9)


def test_a_cut_keeps_the_heaviest_states_and_a_fair_share_of_the_rest() -> None:
    from fow.obscuro import belief as belief_module
    belief = Belief(chess.WHITE, rng=random.Random(3))
    states = [FowBoard() for _ in range(1000)]
    weights = [1000.0 - index for index in range(1000)]          # heaviest first, all different
    kept, kept_weights = belief._cut(states, weights, 200)
    head = int(belief_module.HEAD_SHARE * 200)
    where = {id(state): index for index, state in enumerate(states)}
    assert len(kept) == len(kept_weights) == 200
    assert [where[id(state)] for state in kept[:head]] == list(range(head))  # the heaviest, in order
    assert kept_weights[:head] == weights[:head]                             # and untouched
    drawn = [where[id(state)] for state in kept[head:]]
    assert min(drawn) >= head and len(set(drawn)) == 200 - head
    scale = (1000 - head) / (200 - head)                          # each drawn state stands for this many
    assert kept_weights[head:] == pytest.approx([weights[index] * scale for index in drawn])
    # So the weight of the light states is carried, not dropped: on average over draws it
    # is what it was. Here, one draw: within a quarter.
    assert sum(kept_weights[head:]) == pytest.approx(sum(weights[head:]), rel=0.25)

    same, same_weights = belief._cut(states, [1.0] * 1000, 200)   # equal weights: a plain sample
    assert len(same) == 200 and same_weights == [1.0] * 200


def test_limit_and_cap_use_the_weights_once_there_are_any() -> None:
    belief = sampled_belief(chess.WHITE, [FowBoard() for _ in range(400)])
    belief._weights = [float(index + 1) for index in range(400)]
    belief.weighted = True
    heaviest = belief.states[-50:]
    belief.limit(100)
    assert len(belief) == 100 and len(belief.weights) == 100 and belief.max_states == 100
    assert all(any(state is kept for kept in belief.states) for state in heaviest)


def test_weights_are_reset_if_the_states_are_replaced_from_outside() -> None:
    belief = Belief(chess.WHITE)
    belief._weights = [0.25]
    belief.states = [FowBoard(), FowBoard(), FowBoard()]
    assert belief.weights == [1.0, 1.0, 1.0]


def test_a_top_up_gives_the_new_states_a_fixed_share_of_the_weight() -> None:
    from fow.obscuro import belief as belief_module
    truth = FowBoard("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    obs = observation(truth, chess.WHITE)
    belief = sampled_belief(chess.WHITE, [truth.copy(stack=False)])
    belief._weights = [4.0]
    belief.weighted = True
    belief.replenish(obs)
    added = len(belief) - 1
    assert added > 50 and belief.weights[0] == 4.0
    assert sum(belief.weights[1:]) == pytest.approx(belief_module.REPLENISH_MASS * 4.0)
    assert len(set(belief.weights[1:])) == 1  # shared equally


def test_a_repair_keeps_the_weights() -> None:
    guess = FowBoard("rnbqk2r/ppppbppp/5n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1")
    other = FowBoard("rnbqk2r/ppppbppp/7n/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1")
    truth = FowBoard("rnbqkbnr/ppp2pp1/3p3p/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1")
    belief = sampled_belief(chess.WHITE, [guess, other])
    belief._weights = [1.0, 0.125]
    belief.weighted = True
    truth.push_uci("d8h4")
    states, weights = belief._repaired(observation(truth, chess.WHITE), chess.WHITE)
    assert len(states) == len(weights) == 2 and sorted(weights) == [0.125, 1.0]


def test_a_policy_that_fails_is_ignored() -> None:
    def broken(boards, counts):
        raise RuntimeError("no engine today")

    board = FowBoard()
    belief = Belief(chess.WHITE, rng=random.Random(0))
    belief.observe(observation(board, chess.WHITE))
    board.push_uci("a2a3")
    belief.observe(observation(board, chess.WHITE), own_move=chess.Move.from_uci("a2a3"))
    board.push_uci("g8f6")
    belief.observe(observation(board, chess.WHITE), policy=broken)
    assert len(belief) == 20 and set(belief.weights) == {1.0} and not belief.weighted
