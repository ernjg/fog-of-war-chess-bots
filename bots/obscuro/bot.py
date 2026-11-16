#!/usr/bin/env python3
"""Reduced Obscuro: a belief set, searched with Stockfish when it is available and
otherwise with a depth-2 imperfect-information subgame solved by PCFR+."""
from __future__ import annotations

import argparse
import atexit
import os
import random
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

# Make `fow` importable from the flat packaged layout (fow/ next to bot.py)
# or from the repo layout (bots/<name>/bot.py with fow/ at the repo root).
_HERE = Path(__file__).resolve().parent
for _root in (_HERE, *_HERE.parents[1:2]):
    if (_root / "fow").is_dir():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break  # a copy that carries its own fow/ uses that one, wherever it is unpacked

import chess  # noqa: E402

from fow.obscuro.belief import Belief  # noqa: E402
from fow.obscuro.engine import EnginePool  # noqa: E402
from fow.obscuro.opponent import POLICY_SECONDS, OpponentPolicy  # noqa: E402
from fow.obscuro.position_set import MAX_STATES as FULL_SET_STATES, PositionSet  # noqa: E402
from fow.obscuro.search import move_budget, own_placement, search  # noqa: E402
from fow.obscuro.stockfish_search import stockfish_search  # noqa: E402
from fow.protocol import Agent, log, run  # noqa: E402
from uniform_random import ObservationTracker, candidates  # noqa: E402  (starter kit)

MIN_SEARCH_SECONDS = 0.1  # below this the search cannot build a root; play the fallback move
BRIEF_SEARCH_SECONDS = 0.4    # a move gets at least this much search ...
HEALTHY_CLOCK_SECONDS = 20.0  # ... while this much is left on the clock
BELIEF_SHARE = 0.4            # of a move's time, at most, for updating the belief
MIN_BELIEF_STATES = 128       # the belief is not cut below this to save time
POLICY_TIME_SHARE = 0.15      # of a move's time, at most, for judging the opponent's moves
DEFAULT_ENGINE = _HERE / "stockfish" / "src" / "stockfish"  # where build.sh leaves it
DEFAULT_POSITIONS = _HERE / "positions"                     # and the position-set helper
ENGINE_START_SECONDS = 8.0    # the arena allows 15 s before "ready"
ENGINE_RESTART_SECONDS = 3.0  # at most, on our clock, to replace an engine that died
FALLBACK_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                   chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


class ObscuroAgent(Agent):
    def __init__(self, seed: int | None, max_states: int, move_time: float | None,
                 engine: Path | None = None, engine_count: int = 2, weigh_belief: bool = True,
                 positions: Path | None = None):
        self.rng = random.Random(seed)
        self.max_states = max_states      # the cap of a belief kept in Python
        self.positions = positions        # the position-set helper, or None to do without
        self.belief: Belief | PositionSet | None = None
        self.belief_ceiling = max_states  # the most states the belief in use may hold
        self.helper_lost = False          # whether the loss of the helper has been logged
        self.move_time = move_time
        self.engine = engine              # the Stockfish binary, or None to do without
        self.engine_count = engine_count
        self.pool: EnginePool | None = None
        self.engine_start_seconds = 0.0  # how long the engines took to start, for restarts
        self.engine_deaths = 0           # engine losses reported in the log so far
        self.weigh_belief = weigh_belief  # False: every unseen opponent move counts alike
        self.opponent_policy: OpponentPolicy | None = None
        self.policy_logged = (0, 0)      # its answered and asked counts at our last move

    def reset(self, color: bool, base: float, inc: float) -> None:
        self.side = color
        self.increment = inc
        self.tracker = ObservationTracker(color)
        self.last_move: chess.Move | None = None
        self.plies = 0               # observations received = plies played so far + 1
        self.observe_seconds = 0.0   # belief-update time this turn; it runs on our clock
        self.state_seconds: float | None = None  # what updating the belief costs per state
        self.move_seconds = self.move_time or move_budget(base, inc)  # what a move may take
        self.belief_ok = True
        self.fallbacks = 0
        # Where our pieces have stood: at the start and after each move of ours, with the
        # number of times. A position can only repeat if they stand as they did before.
        self.stood: Counter[str] = Counter()
        log(f"obscuro: playing {'white' if color else 'black'} at {base:g}+{inc:g}")
        self.close()
        self.belief = self._new_belief(color)
        self.pool = self._start_engines()

    def close(self) -> None:
        """Stop the engines and the helper. Safe to call at any time, more than once."""
        self._stop_engines()
        self._stop(getattr(self.belief, "close", None))

    def _stop_engines(self) -> None:
        """Stop the engines only. The position set is still wanted without them."""
        pool, self.pool = self.pool, None
        self._stop(getattr(pool, "close", None))

    @staticmethod
    def _stop(stop) -> None:
        if stop is not None:
            try:
                stop()
            except Exception:
                traceback.print_exc(file=sys.stderr)

    def _new_belief(self, color: bool) -> Belief | PositionSet:
        """The set of possible positions: kept in full by the compiled helper if there is
        one that works, and otherwise by Python, capped at a number it has the time for."""
        self.helper_lost = False
        if self.positions is not None and self.positions.is_file():
            started = time.monotonic()
            try:
                belief = PositionSet(color, [str(self.positions)], FULL_SET_STATES, self.rng)
            except Exception as error:
                log(f"obscuro: the position-set helper did not start ({error}); "
                    "keeping the set in Python")
            else:
                log(f"obscuro: position-set helper ready in {time.monotonic() - started:.2f}s, "
                    f"binary {self.positions}")
                self.belief_ceiling = FULL_SET_STATES
                return belief
        elif self.positions is not None:
            log(f"obscuro: no position-set helper at {self.positions}; keeping the set in Python")
        self.belief_ceiling = self.max_states
        return Belief(color, self.max_states, self.rng)

    def _note_helper(self) -> None:
        """Say once when the helper has been lost; the set is then a Python belief."""
        failure = getattr(self.belief, "failure", "")
        if failure and not self.helper_lost:
            self.helper_lost = True
            self.belief_ceiling = self.max_states
            self.state_seconds = None  # Python's cost per state has yet to be measured
            log(f"obscuro: position-set helper lost ({failure}); carrying on in Python "
                f"from {len(self.belief)} states")

    def _start_engines(self) -> EnginePool | None:
        """Stockfish, if there is a working one. Whatever goes wrong here, the bot still
        plays: without engines it uses the PCFR+ search."""
        if self.engine is None:
            log("obscuro: stockfish is switched off; using the PCFR+ search")
            return None
        if not self.engine.is_file():
            log(f"obscuro: no stockfish at {self.engine}; using the PCFR+ search")
            return None
        started = time.monotonic()
        try:
            pool = EnginePool.start([str(self.engine)], self.engine_count,
                                    started + ENGINE_START_SECONDS, cwd=str(self.engine.parent))
        except Exception:
            log("obscuro: starting stockfish failed; using the PCFR+ search")
            traceback.print_exc(file=sys.stderr)
            return None
        self.engine_deaths = pool.deaths
        # What an engine that works needs to start; with none, nothing is known yet.
        self.engine_start_seconds = pool.start_seconds if pool.ready_count() else 0.0
        if pool.ready_count() == 0:
            # The pool is kept: the first moves have the time to try again (_restart_engines).
            log(f"obscuro: stockfish did not start ({pool.failure}); using the PCFR+ search "
                "until it does")
            return pool
        log(f"obscuro: stockfish ready: {pool.ready_count()} of {self.engine_count} engines "
            f"in {time.monotonic() - started:.2f}s, binary {self.engine}"
            + (f"; missing: {pool.failure}" if pool.ready_count() < self.engine_count else ""))
        return pool

    def observe(self, obs: str) -> None:
        started = time.monotonic()
        self.tracker.observe(obs)
        to_move = chess.WHITE if self.plies % 2 == 0 else chess.BLACK
        if self.plies == 0:
            self.stood[own_placement(obs, self.side)] += 1  # the starting position counts too
        self.plies += 1
        own_move, self.last_move = self.last_move, None
        try:
            if not self.belief_ok:
                raise RuntimeError("belief was unusable; rebuilding from the observation")
            self.belief.observe(obs, own_move=own_move,
                                policy=None if own_move is not None else self._policy())
            self._note_helper()
            seconds, states = self.belief.update_cost
            if own_move is None and states >= MIN_BELIEF_STATES:  # enough to measure by
                self.state_seconds = seconds / states
        except Exception:
            self._rebuild_belief(obs, to_move)
            self._note_helper()
        self.observe_seconds += time.monotonic() - started

    def _policy(self) -> OpponentPolicy | None:
        """How likely each of the opponent's moves is, as Stockfish judges them, for
        weighting the belief; None without a running engine or when switched off (all
        moves then count alike)."""
        pool = self.pool
        if not self.weigh_belief or pool is None or pool.ready_count() == 0:
            return None
        if self.opponent_policy is None or self.opponent_policy.pool is not pool:
            self.opponent_policy = OpponentPolicy(pool)
            self.policy_logged = (0, 0)
        self.opponent_policy.seconds = min(POLICY_SECONDS, POLICY_TIME_SHARE * self.move_seconds)
        return self.opponent_policy

    def _rebuild_belief(self, obs: str, to_move: chess.Color) -> None:
        """The exact update failed: project the old states onto what we see now.

        The result agrees with the observation but is no longer exact. If even
        this fails, the belief is marked unusable and act() plays fallback moves
        until a later rebuild succeeds.
        """
        log("obscuro: belief update failed, rebuilding from the observation")
        traceback.print_exc(file=sys.stderr)
        try:
            self.belief.repair(obs, to_move)
            if not self.belief.states:
                raise RuntimeError("no states to rebuild from")
            self.belief_ok = True
        except Exception:
            log("obscuro: belief rebuild failed, playing fallback moves until it recovers")
            traceback.print_exc(file=sys.stderr)
            self.belief_ok = False

    def act(self, remaining_time: float) -> str | None:
        spent, self.observe_seconds = self.observe_seconds, 0.0
        moves = self._legal_moves()
        if not moves:
            return None
        try:
            self._fit_belief_to_clock(remaining_time - spent)
            moves = self._supported(moves)
        except Exception:
            traceback.print_exc(file=sys.stderr)
        if len(moves) == 1:
            move = moves[0]
        else:
            try:
                move = self._search(moves, remaining_time, spent)
            except Exception:
                log("obscuro: search failed, playing a fallback move")
                traceback.print_exc(file=sys.stderr)
                move = self._fallback_move(moves)
        self.stood[own_placement(self.tracker.current, self.side, move)] += 1
        self.tracker.record_move(move)
        self.last_move = move
        return move.uci()

    def _fit_belief_to_clock(self, left: float) -> None:
        """Keep the belief small enough for its update to fit the clock.

        The update tries every move of every state, so it costs time in proportion to
        the number of states, and it runs on our clock before the search can start. On a
        slow machine a full set takes longer than a move may: the search would be left
        with nothing, and the clock would run down whatever we did. So the cap follows
        the clock: as many states as BELIEF_SHARE of this move's time pays for, at the
        cost per state last measured. A larger set is cut down now (it is then a sample);
        the cap goes back up once the clock affords half as many again, or all of them.
        """
        if self.move_time:
            return
        self.move_seconds = move_budget(max(left, 0.0), self.increment)
        if isinstance(self.belief, PositionSet):
            self.belief.allowance = BELIEF_SHARE * self.move_seconds  # the helper stops there
        if self.state_seconds is None or not self.belief_ok:
            return
        allowed = BELIEF_SHARE * self.move_seconds
        affordable = int(allowed / self.state_seconds)
        target = min(self.belief_ceiling, max(MIN_BELIEF_STATES, affordable))
        cap = self.belief.max_states
        if target < cap or target >= min(1.5 * cap, self.belief_ceiling):
            self.belief.limit(target)
            self._note_helper()

    def _supported(self, moves: list[chess.Move]) -> list[chess.Move]:
        """``moves`` without the en passant captures that no belief state allows.

        The tracker infers en passant from the last two observations. A belief rebuilt
        after a failed update does not have it, and both searches leave out every state
        that does not allow every move: with such a capture in the list they would have
        no state left and the move would be played unsearched.
        """
        view = self.tracker.current
        doubtful = [move for move in moves
                    if view[move.from_square] in "Pp" and view[move.to_square] == "-"
                    and chess.square_file(move.from_square) != chess.square_file(move.to_square)]
        if not doubtful or not self.belief_ok:
            return moves
        known = self.belief.ep_squares()
        dropped = [move for move in doubtful if move.to_square not in known]
        if not dropped or len(dropped) == len(moves):
            return moves
        log(f"obscuro: no belief state allows {' '.join(move.uci() for move in dropped)}; "
            "searching the other moves")
        return [move for move in moves if move not in dropped]

    def _legal_moves(self) -> list[chess.Move]:
        try:
            return self.tracker.legal_moves()
        except Exception:
            # The starter's en passant inference can raise; without the previous
            # observation it cannot, at the cost of not offering en passant.
            log("obscuro: legal move generation failed, retrying without en passant inference")
            traceback.print_exc(file=sys.stderr)
            return candidates(self.tracker.current, self.side, self.tracker.rights)[1]

    def _search(self, moves: list[chess.Move], remaining_time: float, spent: float) -> chess.Move:
        started = time.monotonic()
        if self.move_time:
            budget = self.move_time
        else:
            # The belief update already used `spent` seconds of this turn's clock.
            left = remaining_time - spent
            budget = move_budget(left, self.increment) - spent
            if budget < BRIEF_SEARCH_SECONDS and left >= HEALTHY_CLOCK_SECONDS:
                # A slow belief update has used up this move's slice. With this much on
                # the clock a short search is still worth far more than the fallback move.
                budget = BRIEF_SEARCH_SECONDS
        # A fixed --move-time is a deliberate choice (tests use tiny ones); the floor
        # only guards the clock-based budget.
        if not self.belief_ok or (not self.move_time and budget < MIN_SEARCH_SECONDS):
            log(f"obscuro: no search (belief_ok={self.belief_ok} budget={budget:.2f}s "
                f"belief_update={spent:.2f}s)")
            return self._fallback_move(moves)
        repeats = [self.stood[own_placement(self.tracker.current, self.side, move)] for move in moves]
        repeat_counts = repeats if any(repeats) else None
        if self.pool is not None:
            move = self._stockfish_move(moves, started + budget, spent, repeat_counts)
            if move is not None:
                return move
            budget -= time.monotonic() - started  # what is left goes to the PCFR+ search
            if not self.move_time and budget < MIN_SEARCH_SECONDS:
                log(f"obscuro: {budget:.2f}s left for this move; playing a fallback move")
                return self._fallback_move(moves)
            log(f"obscuro: PCFR+ search with the {budget:.2f}s left")
        result = search(self.belief.states, moves, self.side, budget, self.rng,
                        repeat_counts=repeat_counts)
        if result is None:
            log(f"obscuro: no usable root among {len(self.belief)} states")
            return self._fallback_move(moves)
        log(f"obscuro: {result.move.uci()} value={result.value:+.3f} gap={result.nash_gap:.3f} "
            f"|P|={self._belief_size()} roots={result.roots} "
            f"iters={result.iterations} "
            f"repairs={self.belief.repairs} budget={budget:.2f}s belief_update={spent:.2f}s"
            + (" repeat_avoided" if result.repeat_avoided else ""))
        return result.move

    def _stockfish_move(self, moves: list[chess.Move], deadline: float, spent: float,
                        repeat_counts: list[int] | None) -> chess.Move | None:
        """The Stockfish search's move, or None if it has none for this position."""
        pool = self.pool
        try:
            self._restart_engines(pool, deadline)
            if pool.ready_count() == 0 and pool.restarts >= pool.restart_limit:
                log(f"obscuro: stockfish is gone for this game ({pool.failure}); "
                    "using the PCFR+ search")
                self._stop_engines()  # not close(): the position-set helper stays
                return None
            budget = deadline - time.monotonic()
            weights = self.belief.weights if self.belief.weighted else None
            result = stockfish_search(pool, self.belief.states, moves, self.side, budget,
                                      self.rng, repeat_counts, weights)
        except Exception:
            log("obscuro: stockfish search failed")
            traceback.print_exc(file=sys.stderr)
            return None
        if pool.deaths > self.engine_deaths:  # say why, while the reason is still known
            self.engine_deaths = pool.deaths
            log(f"obscuro: stockfish engine lost ({pool.failure}); "
                f"{pool.ready_count()} of {self.engine_count} running")
        if result is None:
            log(f"obscuro: no stockfish result ({pool.ready_count()} engines running)")
            return None
        depth = "-" if result.depth is None else f"{result.depth[0]}-{result.depth[1]}"
        log(f"obscuro: sf {result.move.uci()} value={result.value:+.3f} risk={result.risk:.2f} "
            f"|P|={self._belief_size()} scan={result.scanned} "
            f"roots={result.roots}/{result.sampled} depth={depth} eng={pool.ready_count()} "
            f"repairs={self.belief.repairs} budget={budget:.2f}s "
            f"belief_update={spent:.2f}s" + self._policy_note()
            + (" repeat_avoided" if result.repeat_avoided else ""))
        return result.move

    def _policy_note(self) -> str:
        """For the log: of the positions the opponent policy was asked about since our
        last move, how many the engines answered in time (the rest got equal odds)."""
        policy = self.opponent_policy
        if policy is None:
            return ""
        answered, asked = policy.answered - self.policy_logged[0], policy.asked - self.policy_logged[1]
        self.policy_logged = (policy.answered, policy.asked)
        return f" policy={answered}/{asked}" if asked > 0 else ""

    def _belief_size(self) -> str:
        """For the log: the number of states, "~" if they are only a sample, the cap where
        the clock has lowered it, and, once the states have weights, how many equally
        likely states those weights amount to."""
        size = f"{len(self.belief)}{'' if self.belief.exact else '~'}"
        cap = self.belief.max_states
        if cap < self.belief_ceiling:
            size = f"{size}/{cap}"
        return f"{size} ess={self.belief.effective_size():.0f}" if self.belief.weighted else size

    def _restart_engines(self, pool: EnginePool, deadline: float) -> None:
        """Replace engines that died, if this move can afford it.

        Starting an engine runs on our clock and each attempt uses up one of the few
        restarts a game gets. So none is made unless the time allowed (half of what this
        move has left, at most) clearly exceeds what starting the engines took at the
        beginning of the game; otherwise the move is searched with the engines that remain.
        """
        if pool.ready_count() >= self.engine_count or pool.restarts >= pool.restart_limit:
            return
        allowance = min(ENGINE_RESTART_SECONDS, (deadline - time.monotonic()) / 2)
        if allowance < 1.5 * self.engine_start_seconds:
            return
        started = pool.restart(time.monotonic() + allowance)
        if started:
            self.engine_start_seconds = pool.start_seconds
        log(f"obscuro: restarted stockfish: {started} started within {allowance:.2f}s, "
            f"{pool.ready_count()} of {self.engine_count} running, "
            f"{pool.restarts} of {pool.restart_limit} restarts used"
            + (f"; missing: {pool.failure}" if pool.ready_count() < self.engine_count else ""))

    def _fallback_move(self, moves: list[chess.Move]) -> chess.Move:
        """Needs only the current observation: best capture that does not leave our
        king attacked by a piece we can see. Never raises."""
        self.fallbacks += 1
        try:
            board = candidates(self.tracker.current, self.side, self.tracker.rights)[0]

            def score(move: chess.Move) -> float:
                target = board.piece_at(move.to_square)
                value = FALLBACK_VALUES[target.piece_type] * 10 if target else 0
                if move.promotion:
                    value += FALLBACK_VALUES[move.promotion] * 5
                board.push(move)
                king = board.king(self.side)
                if king is not None and board.is_attacked_by(not self.side, king):
                    value -= 1000
                board.pop()
                return value + self.rng.random()

            return max(moves, key=score)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return self.rng.choice(moves)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-states", type=int, default=1500)
    parser.add_argument("--move-time", type=float, default=None,
                        help="fixed seconds per move instead of the clock-based budget")
    parser.add_argument("--stockfish", default=os.environ.get("FOW_STOCKFISH", str(DEFAULT_ENGINE)),
                        help="Stockfish binary (default: $FOW_STOCKFISH, else the one build.sh "
                             "makes); 'off' plays without it")
    parser.add_argument("--engines", type=int, default=2, help="Stockfish processes to run")
    parser.add_argument("--equal-odds", action="store_true",
                        help="count every unseen opponent move as equally likely, instead of "
                             "weighting the belief by Stockfish's judgement of the moves")
    parser.add_argument("--positions", default=os.environ.get("FOW_POSITIONS", str(DEFAULT_POSITIONS)),
                        help="position-set helper binary (default: $FOW_POSITIONS, else the one "
                             "build.sh makes); 'off' keeps the set in Python, capped at --max-states")
    args = parser.parse_args()
    off = ("", "off", "none", "0")
    engine = None if args.stockfish.strip().lower() in off else Path(args.stockfish).expanduser().resolve()
    positions = None if args.positions.strip().lower() in off else Path(args.positions).expanduser().resolve()
    agent = ObscuroAgent(args.seed, args.max_states, args.move_time, engine, max(1, args.engines),
                         weigh_belief=not args.equal_odds, positions=positions)
    atexit.register(agent.close)
    run(agent)


if __name__ == "__main__":
    main()
