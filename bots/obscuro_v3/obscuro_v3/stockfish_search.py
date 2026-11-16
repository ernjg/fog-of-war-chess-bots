"""Move choice with Stockfish: score our moves on sampled belief states and average.

On each sampled position Stockfish searches every orthodox-legal move (MultiPV), which
gives each of our moves a value there. A move that leaves our king capturable on that
position is an immediate loss instead. The move with the best average is played.

Stockfish plays the opponent with full knowledge of each sampled position. The depth-2
PCFR+ search ends up modelling the opponent the same way (two different belief states
never look alike to the opponent, who always sees its own pieces), but this looks several
plies further and uses a real evaluation.
"""
from __future__ import annotations

import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

import chess
import numpy as np

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard

from .engine import EnginePool, Job, mate_value
from .rules import side_to_move_wins
from .search import choose_action

MAX_ROOTS = 64             # belief states Stockfish scores per move
SCAN_STATES = 256          # belief states checked for moves that lose the king at once
SCAN_SHARE = 0.1           # of the budget, at most, for that check
MAX_DEPTH = 12
MIN_SLICE = 0.02           # seconds of search per position, at least
MAX_SLICE = 1.0            # and at most: with few states left, bank the time instead
RESERVE = 0.06             # seconds kept back for stopping the engines and choosing
MIN_ENGINE_SECONDS = 0.05
DRAW = 0.0
# A belief state in which our king is attacked counts this many times. The belief treats all
# of the opponent's unseen moves as equally likely, but an opponent who can attack our king
# out of sight usually does: over 1,053 recorded decisions, when a small share of states had
# the king attacked it really was attacked about six times as often as that share. (1,965
# decisions from later games put it near 4.5; the choice of move hardly depends on it.)
ATTACKED_WEIGHT = 6.0
WIN, LOSS = 1.0, -1.0


@dataclass(frozen=True)
class MoveClasses:
    """Indices into our candidate moves, split by what they are on one position."""
    legal: tuple[int, ...]     # orthodox-legal: Stockfish scores these
    suicide: tuple[int, ...]   # our king can be captured after the move
    fow_only: tuple[int, ...]  # castling out of or through attack: legal only in Fog of War,
    #                            and the king is safe where it lands


@dataclass(frozen=True)
class StockfishResult:
    move: chess.Move
    value: float
    risk: float                      # weighted share of scanned states where it loses the king
    scanned: int
    sampled: int                     # states sent to the engine
    roots: int                       # states it scored completely
    depth: tuple[int, int] | None    # shallowest and deepest completed search
    repeat_avoided: bool
    values: tuple[float, ...]        # the average for each of our moves, in their order
    risks: tuple[float, ...]         # and the share of scanned states where each loses the king


def king_capturable_after(board: FowBoard, move: chess.Move) -> bool:
    """Whether playing ``move`` leaves the mover's king capturable (an immediate loss)."""
    board.push(move)
    try:
        return side_to_move_wins(board)
    finally:
        board.pop()


def classify(board: FowBoard, moves: Sequence[chess.Move]) -> MoveClasses | None:
    """Split our candidate ``moves`` on one possible position.

    None if the position contradicts what we know: a candidate cannot be played there, or
    we could already capture the king (the game would be over).
    """
    if side_to_move_wins(board) or not set(board.generate_pseudo_legal_moves()).issuperset(moves):
        return None
    # For every move except castling, "orthodox-legal" is exactly "our king is not attacked
    # afterwards". FowBoard generates castling without attack tests, and python-chess
    # trusts the generator there, so castling is asked of the orthodox generator directly.
    orthodox = set(board.generate_legal_moves())
    orthodox_castling = set(chess.Board.generate_castling_moves(board))
    legal, suicide, fow_only = [], [], []
    for index, move in enumerate(moves):
        if board.is_castling(move):
            if move in orthodox_castling:
                legal.append(index)
            elif king_capturable_after(board, move):
                suicide.append(index)
            else:
                fow_only.append(index)
        elif move in orthodox:
            legal.append(index)
        else:
            suicide.append(index)
    return MoveClasses(tuple(legal), tuple(suicide), tuple(fow_only))


def no_safe_reply(board: FowBoard) -> bool:
    """The side to move loses whatever it plays: every move leaves its king capturable, or
    it has none. Checkmate and stalemate both come to this in Fog of War, unless castling
    (allowed out of check here) still gets the king to safety."""
    # Every move is tried, rather than asking python-chess for a legal one: it takes
    # FowBoard's castling for legal even where the king lands on an attacked square.
    return all(king_capturable_after(board, move) for move in board.generate_pseudo_legal_moves())


def engine_accepts(board: chess.Board) -> bool:
    """Whether Stockfish 19 will take this position.

    It exits on a position that fails the checks of its ``Position::set``, mirrored here.
    Positions reached by play always pass; a repaired belief state may not.
    """
    if board.pawns & (chess.BB_RANK_1 | chess.BB_RANK_8):
        return False
    for color in chess.COLORS:
        own = board.occupied_co[color]
        if chess.popcount(board.kings & own) != 1:
            return False
        pawns = chess.popcount(board.pawns & own)
        promoted = (max(chess.popcount(board.knights & own) - 2, 0)
                    + max(chess.popcount(board.bishops & own) - 2, 0)
                    + max(chess.popcount(board.rooks & own) - 2, 0)
                    + max(chess.popcount(board.queens & own) - 1, 0))
        if pawns > 8 or promoted > 8 - pawns:
            return False
    if board.fullmove_number > 100000:
        return False
    return not side_to_move_wins(board)  # "King can be captured"


def engine_fen(board: chess.Board) -> str:
    """FEN for the engine, with a fifty-move clock it can use.

    A state's clock below 100 is that state's own count and is passed on: at 99 Stockfish
    rightly scores every quiet move as the draw the referee would declare. A clock of 100
    or more cannot be the real one (the game would be over); it only says that the
    opponent moved a pawn out of our sight at some point. Passed on as it is, or as 99,
    it would turn every quiet move into a draw, so it is replaced by the largest clock
    that keeps the draw beyond what the search can reach.
    """
    fields = board.fen().split(" ")
    clock = board.halfmove_clock
    fields[4] = str(max(clock, 0) if clock < 100 else 99 - MAX_DEPTH)
    return " ".join(fields)


@dataclass
class _Root:
    state: FowBoard
    classes: MoveClasses
    wins: list[int]  # our moves after which the opponent has no safe reply


def _prepare_root(state: FowBoard, classes: MoveClasses, our_moves: Sequence[chess.Move]
                  ) -> tuple[_Root, list[tuple[Job, int]]] | None:
    """The engine jobs for one belief state, each with the move index it scores (-1 for the
    state itself, which scores every orthodox-legal move). None if the engine cannot take it."""
    if not engine_accepts(state):
        return None
    root = _Root(state, classes, [])
    jobs: list[tuple[Job, int]] = []
    if classes.legal:
        jobs.append((Job(engine_fen(state), MAX_DEPTH), -1))
    for index in classes.fow_only:
        # Stockfish cannot play this move, so it scores the position after it instead.
        child = state.copy(stack=False)
        child.push(our_moves[index])
        if no_safe_reply(child):
            root.wins.append(index)
        elif engine_accepts(child):
            jobs.append((Job(engine_fen(child), MAX_DEPTH), index))
        else:
            return None
    return root, jobs


@dataclass(frozen=True)
class Evidence:
    """What the scan and the engine found for one decision, before any averaging."""
    scan_attacked: np.ndarray  # (S,)   our king is attacked on this scanned state
    scan_suicide: np.ndarray   # (S, n) the move loses the king on this scanned state
    root_attacked: np.ndarray  # (R,)   the same two, for the states the engine scored in full
    root_suicide: np.ndarray   # (R, n)
    root_values: np.ndarray    # (R, n) value of each move there; LOSS where it loses the king
    sampled: int               # states sent to the engine
    depths: tuple[int, ...]    # search depth completed on each state that had legal moves


def gather(pool: EnginePool, states: Sequence[FowBoard], our_moves: Sequence[chess.Move],
           side: chess.Color, deadline: float, rng: random.Random) -> Evidence | None:
    """Scan sampled ``states`` for moves that lose the king and have Stockfish score as many
    as fit before ``deadline``. None when nothing usable came of it."""
    start = time.monotonic()
    n_moves = len(our_moves)
    if pool.ready_count() == 0 or deadline - start < MIN_ENGINE_SECONDS:
        return None

    # 1. On a wide sample, find the moves that lose the king at once.
    scanned: list[tuple[FowBoard, MoveClasses]] = []
    scan_until = start + SCAN_SHARE * (deadline - start)
    for state in rng.sample(list(states), len(states)):
        now = time.monotonic()
        if len(scanned) >= SCAN_STATES or now > deadline or (scanned and now > scan_until):
            break
        classes = classify(state, our_moves) if state.turn == side else None
        if classes is not None:
            scanned.append((state, classes))
    if not scanned:
        return None
    scan_suicide = np.zeros((len(scanned), n_moves), dtype=bool)
    for row, (_, classes) in enumerate(scanned):
        scan_suicide[row, list(classes.suicide)] = True
    scan_attacked = np.array([state.is_check() for state, _ in scanned])

    # 2. Have Stockfish score the first of those states, as many as the time allows.
    engine_seconds = deadline - time.monotonic()
    if engine_seconds < MIN_ENGINE_SECONDS:
        return None
    max_jobs = max(1, int(engine_seconds * pool.ready_count() / MIN_SLICE))
    roots: list[_Root] = []
    rows: list[int] = []                # the scanned state each root is
    jobs: list[Job] = []
    owners: list[tuple[int, int]] = []  # (root, move index or -1) of each job
    for row, (state, classes) in enumerate(scanned):
        if len(roots) >= MAX_ROOTS or len(jobs) >= max_jobs:
            break
        prepared = _prepare_root(state, classes, our_moves)
        if prepared is None:
            continue
        root, root_jobs = prepared
        for job, index in root_jobs:
            jobs.append(job)
            owners.append((len(roots), index))
        roots.append(root)
        rows.append(row)
    if not roots:
        return None
    results = pool.run(jobs, deadline, MIN_SLICE, MAX_SLICE) if jobs else []

    # 3. One row of values per state; a state missing any value is left out.
    values = np.full((len(roots), n_moves), np.nan)
    usable = np.ones(len(roots), dtype=bool)
    depths: list[int] = []
    for r, root in enumerate(roots):
        values[r, list(root.classes.suicide)] = LOSS
        values[r, root.wins] = WIN  # castling that leaves the opponent no safe reply
    for (r, index), result in zip(owners, results, strict=True):
        if result is None:
            usable[r] = False
        elif index < 0:
            legal = roots[r].classes.legal
            ucis = [our_moves[i].uci() for i in legal]
            depth = result.complete_depth(ucis)
            if depth is None:
                usable[r] = False
            else:
                values[r, list(legal)] = [result.scores[uci][depth] for uci in ucis]
                depths.append(depth)
        else:
            reply = None if result.no_moves else result.best()  # the opponent's best there
            if reply is None:
                usable[r] = False
            else:
                values[r, index] = -reply
    usable &= ~np.isnan(values).any(axis=1)
    for r in np.flatnonzero(usable):
        _apply_fog_rules(roots[r], our_moves, values[r])
    use = np.flatnonzero(usable)
    kept = np.array(rows, dtype=int)[use]
    # A state where every move loses the king needs no engine, so it is "scored" even if
    # every engine failed. Alone, such states say nothing about which move to prefer.
    if len(use) == 0 or (scan_suicide[kept].all() and not scan_suicide.all()):
        return None
    return Evidence(scan_attacked, scan_suicide, scan_attacked[kept], scan_suicide[kept],
                    values[use], len(roots), tuple(depths))


def _apply_fog_rules(root: _Root, our_moves: Sequence[chess.Move], values: np.ndarray) -> None:
    """Correct Stockfish's values on one state where this game's rules differ from chess."""
    state = root.state
    mate_in_one = mate_value(1)
    # Stalemate is a draw to Stockfish (exactly 0); here the side with no safe move must
    # still move and loses its king. Checkmate is the same thing, with one exception:
    # the king may castle out of check here. Where that saves it, what Stockfish calls
    # mate is only a check, and nothing it reported says what the move is worth.
    only_a_check = []
    for index in root.classes.legal:
        if values[index] == DRAW or values[index] == mate_in_one:
            state.push(our_moves[index])
            try:
                trapped = no_safe_reply(state)
            finally:
                state.pop()
            if trapped:
                root.wins.append(index)
            elif values[index] == mate_in_one:
                only_a_check.append(index)
    values[root.wins] = WIN
    if only_a_check:
        # Valued like the worst of the other moves there: never preferred to any of them
        # on the strength of a mate that is not one, and the state still speaks for the rest.
        others = [values[index] for index in root.classes.legal + root.classes.fow_only
                  if index not in only_a_check]
        values[only_a_check] = min(others, default=DRAW)
    # At 99 plies without progress a quiet move ends the game as a draw before the
    # opponent has to answer it, even a move that mates. Stockfish puts mate first.
    if state.halfmove_clock == 99:
        for index in root.classes.legal + root.classes.fow_only:
            if not state.is_zeroing(our_moves[index]):
                values[index] = DRAW


def weigh(evidence: Evidence,
          attacked_weight: float = ATTACKED_WEIGHT) -> tuple[np.ndarray, np.ndarray]:
    """(value, risk) of each move from the evidence.

    Every state has weight 1, or ``attacked_weight`` if our king is attacked in it.
    ``risk`` is the weighted share of scanned states in which the move loses the king.
    The value is ``-risk + (1 - risk) * mean``, where ``mean`` is the move's weighted
    average Stockfish value over the scored states in which the king survives it. With a
    weight of 1, and the scanned states being the scored ones, that is the plain mean
    with -1 where the king is lost.
    """
    scan_weight = np.where(evidence.scan_attacked, attacked_weight, 1.0)
    risk = scan_weight @ evidence.scan_suicide / scan_weight.sum()
    root_weight = np.where(evidence.root_attacked, attacked_weight, 1.0)
    safe = ~evidence.root_suicide
    count = root_weight @ safe
    total = root_weight @ np.where(safe, evidence.root_values, 0.0)
    known = count > 0
    # A move that loses the king on every scored state, yet not on every scanned one, has
    # no value to go by. It gets the lowest value of the moves that do: not preferred to
    # any of them, but not written off as a certain loss either.
    unknown = float(np.min(total[known] / count[known])) if known.any() else LOSS
    when_safe = np.where(known, total / np.maximum(count, 1e-12), unknown)
    return -risk + (1.0 - risk) * when_safe, risk


def stockfish_search(pool: EnginePool, states: Sequence[FowBoard],
                     our_moves: Sequence[chess.Move], side: chess.Color, budget: float,
                     rng: random.Random,
                     repeat_counts: Sequence[int] | None = None) -> StockfishResult | None:
    """The move with the best value over sampled ``states``; see ``weigh`` for the value.

    None when it cannot say anything: no engine, no time, no state that fits our view, or
    no state the engine finished. The caller then falls back to the PCFR+ search.
    """
    evidence = gather(pool, states, our_moves, side, time.monotonic() + budget - RESERVE, rng)
    if evidence is None:
        return None
    value, risk = weigh(evidence)

    # Choose: exact ties at random, and not the same shuffle again when winning.
    ranked = value + 1e-9 * np.array([rng.random() for _ in our_moves])
    top = int(np.argmax(ranked))
    strategy = np.zeros(len(our_moves))
    strategy[top] = 1.0
    counts = None if repeat_counts is None else np.asarray(repeat_counts, dtype=float)
    chosen = choose_action(strategy, ranked, float(value[top]), counts)
    depths = evidence.depths
    return StockfishResult(our_moves[chosen], float(value[chosen]), float(risk[chosen]),
                           len(evidence.scan_attacked), evidence.sampled,
                           len(evidence.root_attacked),
                           (min(depths), max(depths)) if depths else None, chosen != top,
                           tuple(float(v) for v in value), tuple(float(r) for r in risk))
