"""The belief set kept in full, by a compiled helper (bots/obscuro/positions.cpp).

Obscuro keeps every position consistent with what it has seen. In Python the update
costs milliseconds per position, so ``belief.Belief`` can afford a few hundred and has to
sample; the helper does the same update in about a microsecond and keeps them all, up
to a cap that is rarely reached.

``PositionSet`` has the interface of ``Belief``, so the bot uses whichever it has. The
positions themselves stay in the helper. What Python sees, as ``states`` and ``weights``,
is the whole set while it is small and otherwise a sample of SAMPLE_STATES draws by
weight (each state once, with the number of times it was drawn as its weight), which is
what the search would have drawn anyway.

Two things are still done by ``Belief``, on that sample, because they are rare and
intricate: rebuilding a set that an observation has emptied, and topping up a thin one
(both can only happen after the cap has cut the set). And if the helper has no answer in
time, or exits, the game goes on with a ``Belief`` started from the last sample.
"""
from __future__ import annotations

import os
import random
import select
import subprocess
import time
from collections.abc import Sequence

import chess

import fow  # noqa: F401  (puts the starter kit on sys.path)
from referee import FowBoard

from .belief import HEAD_SHARE, MIN_POOL, Belief
from .opponent import KING_MISS, OTHER, Policy

SAMPLE_STATES = 1024     # states handed to the search: stockfish_search.SCAN_STATES draws
UNIFORM_STATES = 512     # and, when the set is sampled by weight, this many drawn with equal odds
MAX_STATES = 200_000     # the most the helper keeps; a larger set is cut down, as in Belief
FALLBACK_STATES = 1500   # the cap of the Python belief that takes over if the helper is lost
ASK_STATES = 512         # states per opponent move that the policy is asked about, at most
START_SECONDS = 2.0      # for the helper to answer its first command
ANSWER_SECONDS = 3.0     # for any later answer, beyond the time the command itself was given
EXPAND_SECONDS = 1.5     # for one update of the set, unless ``allowance`` says otherwise
MAX_BUFFER = 64 * 1024 * 1024


class HelperError(RuntimeError):
    """The helper did not answer, or not in a way that can be used."""


class Helper:
    """The helper process: one command, one answer, each with a deadline."""

    def __init__(self, command: Sequence[str], cwd: str | None = None):
        self.dead = False
        self._buffer = b""
        # stdout must be our pipe, never the bot's stdout: that one belongs to the referee.
        # No new session or process group: the helper has to be paused together with the bot.
        self.proc = subprocess.Popen(list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     bufsize=0, cwd=cwd)
        self._in, self._out = self.proc.stdin.fileno(), self.proc.stdout.fileno()
        os.set_blocking(self._in, False)
        os.set_blocking(self._out, False)

    def ask(self, text: str, deadline: float) -> tuple[str, list[str]]:
        """Send one command (several lines for those that carry a table) and return its
        answer: the first line and the lines that line announces."""
        if self.dead:
            raise HelperError("the helper is gone")
        try:
            self._send(text.encode("ascii") + b"\n", deadline)
            header = self._line(deadline)
            words = header.split()
            if not words or words[0] == "err":
                raise HelperError(f"the helper answered {header[:80]!r}")
            more = int(words[2]) if words[0] == "parents" else int(words[1]) if words[0] in ("sample", "dump", "usample", "leaves", "result") else 0
            return header, [self._line(deadline) for _ in range(more)]
        except HelperError:
            self.kill()  # after one bad answer nothing it says can be matched to a question
            raise
        except (OSError, ValueError, IndexError) as error:
            self.kill()
            raise HelperError(f"talking to the helper failed: {error!r}") from error

    def _send(self, data: bytes, deadline: float) -> None:
        while data:
            wait = deadline - time.monotonic()
            if wait <= 0:
                raise HelperError("the helper did not read its input in time")
            _, ready, _ = select.select([], [self._in], [], wait)
            if ready:
                try:
                    data = data[os.write(self._in, data):]
                except BlockingIOError:
                    continue

    def _line(self, deadline: float) -> str:
        while b"\n" not in self._buffer:
            wait = deadline - time.monotonic()
            if wait <= 0:
                raise HelperError("the helper did not answer in time")
            ready, _, _ = select.select([self._out], [], [], wait)
            if not ready:
                continue
            try:
                chunk = os.read(self._out, 1 << 20)
            except BlockingIOError:
                continue
            if not chunk:
                raise HelperError(f"the helper exited ({self.proc.poll()})")
            self._buffer += chunk
            if len(self._buffer) > MAX_BUFFER:
                raise HelperError("the helper's answer is too long")
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode("ascii", "replace").strip()

    def kill(self) -> None:
        if self.dead:
            return
        self.dead = True
        try:
            self.proc.kill()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=1.0)
        except (OSError, subprocess.TimeoutExpired):
            pass
        for stream in (self.proc.stdin, self.proc.stdout):
            try:
                stream.close()
            except OSError:
                pass

    def quit(self) -> None:
        """Ask the helper to exit, then make sure it has."""
        if not self.dead:
            try:
                self._send(b"quit\n", time.monotonic() + 0.2)
                self.proc.wait(timeout=0.5)
            except (HelperError, OSError, subprocess.TimeoutExpired):
                pass
        self.kill()


def _fields(header: str) -> dict[str, str]:
    """The ``name=value`` words of an answer such as ``ok size=20 exact=1 ...``."""
    return dict(word.split("=", 1) for word in header.split()[1:] if "=" in word)


class PositionSet:
    """Every position consistent with our observations, each with a weight; see Belief."""

    def __init__(self, side: chess.Color, command: Sequence[str], max_states: int = MAX_STATES,
                 rng: random.Random | None = None, cwd: str | None = None):
        self.side = side
        self.max_states = max_states
        self.rng = rng or random.Random()
        self.states: list[FowBoard] = [FowBoard()]
        self._weights = [1.0]
        self.uniform_states: list[FowBoard] = []  # see _fetch
        self.weighted = False
        self.exact = True
        self.repairs = 0
        self.update_cost = (0.0, 0)  # seconds the helper spent on the last update, and for how many states
        self.allowance: float | None = None  # seconds one update may take; the bot sets it from the clock
        self.fallback: Belief | None = None  # the Python belief, once the helper is lost
        self.failure = ""                    # why it was lost
        self.asked = 0                       # states the policy was asked about at the last update
        self._size = 1
        self._ess = 1.0
        self._ep: set[int] = set()
        self._started = False
        self.helper = Helper(command, cwd)
        self._ok(f"new {'w' if side else 'b'} {max_states} {self.rng.getrandbits(48)} {HEAD_SHARE!r}",
                 time.monotonic() + START_SECONDS)

    # -- what the bot reads -------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.fallback) if self.fallback is not None else self._size

    @property
    def weights(self) -> list[float]:
        """One weight per state in ``states`` (see the module's docstring)."""
        if self.fallback is not None:
            return self.fallback.weights
        if len(self._weights) != len(self.states):
            self._weights = [1.0] * len(self.states)
        return self._weights

    def effective_size(self) -> float:
        return self.fallback.effective_size() if self.fallback is not None else self._ess

    def ep_squares(self) -> set[int]:
        """The squares a pawn has just skipped in some state: where en passant may be possible."""
        if self.fallback is not None:
            return self.fallback.ep_squares()
        return set(self._ep)

    # -- what the bot does --------------------------------------------------------------

    def observe(self, obs: str, own_move: chess.Move | None = None,
                policy: Policy | None = None) -> None:
        """Filter with the observation after one ply, as ``Belief.observe`` does."""
        if self.fallback is not None:
            self.fallback.observe(obs, own_move=own_move, policy=policy)
            self._mirror()
            return
        to_move = (not self.side) if own_move is not None else self.side if self._started else chess.WHITE
        try:
            if own_move is not None:
                fields = self._ok(f"own {own_move.uci()} {obs}")
            elif self._started:
                fields = self._after_opponent(obs, policy)
            else:
                fields = self._ok(f"init {obs}")
            self.update_cost = (float(fields["ms"]) / 1000.0, int(fields["expanded"]))
            if int(fields["size"]) == 0:
                self._rebuild(obs, to_move)
            elif not self.exact and self._size < MIN_POOL:
                self._top_up(obs)
            self._started = True
            self._fetch()
        except HelperError as error:
            self._fall_back(str(error))
            self.fallback.observe(obs, own_move=own_move, policy=policy)
            self._mirror()

    def repair(self, obs: str, to_move: chess.Color) -> None:
        """Rebuild the set from the current observation alone, when updating it failed."""
        if self.fallback is None:
            try:
                self._rebuild(obs, to_move)
                self._started = True
                self._fetch()
                return
            except HelperError as error:
                self._fall_back(str(error))
        self.fallback.repair(obs, to_move)
        self._mirror()

    def limit(self, max_states: int) -> None:
        """Change the cap; a larger set is cut down to it at once."""
        if self.fallback is not None:
            self.fallback.limit(min(max_states, FALLBACK_STATES))
            self._mirror()
            return
        self.max_states = max_states
        try:
            self._ok(f"limit {max_states}")
        except HelperError as error:
            self._fall_back(str(error))

    def close(self) -> None:
        """Stop the helper. Safe to call at any time, more than once."""
        self.helper.quit()

    # -- the helper ---------------------------------------------------------------------

    def _ok(self, text: str, deadline: float | None = None) -> dict[str, str]:
        """A command whose answer is the state of the set."""
        header, _ = self.helper.ask(text, deadline or time.monotonic() + ANSWER_SECONDS)
        fields = _fields(header)
        try:
            size = int(fields["size"])
            if size:  # 0: nothing fitted, and the set is as it was
                self._size = size
            self.exact = fields["exact"] == "1"
            self.weighted = fields["weighted"] == "1"
            self._ess = float(fields["ess"])
            mask = int(fields["ep"], 16)
            self._ep = {square for square in range(64) if mask >> square & 1}
            float(fields["ms"]), int(fields["expanded"])
        except (KeyError, ValueError) as error:
            self.helper.kill()
            raise HelperError(f"the helper answered {header[:80]!r}") from error
        return fields

    def _after_opponent(self, obs: str, policy: Policy | None) -> dict[str, str]:
        """One ply of the opponent's. The helper finds the successors; the policy says how
        likely the moves were from the heaviest states (the others get equal odds); the
        helper turns that into weights."""
        seconds = self.allowance if self.allowance is not None else EXPAND_SECONDS
        header, rows = self.helper.ask(f"opp {obs} {max(seconds, 0.05) * 1000:.0f} {ASK_STATES if policy is not None else 0}",
                                       time.monotonic() + seconds + ANSWER_SECONDS)
        tables: list[str] = []
        use_policy = policy is not None
        self.asked = len(rows)
        if policy is not None and rows:
            indices, counts, boards = [], [], []
            for row in rows:
                _, index, n_moves, fen = row.split(" ", 3)
                indices.append(int(index))
                counts.append(int(n_moves))
                boards.append(FowBoard(fen))
            try:
                answers = policy(boards, counts)
                if len(answers) != len(boards):
                    raise ValueError("one answer per state")
                for index, table in zip(indices, answers, strict=True):
                    if table is not None:
                        listed = [(uci, odds) for uci, odds in table.items() if uci != OTHER]
                        tables.append(f"t {index} {float(table[OTHER])!r} {len(listed)}"
                                      + "".join(f" {uci} {float(odds)!r}" for uci, odds in listed))
            except Exception:  # a policy that fails is no policy: equal odds
                use_policy, tables = False, []
        return self._ok("\n".join([f"commit {int(use_policy)} {KING_MISS!r} {len(tables)}", *tables]))

    def _fetch(self) -> None:
        """What Python sees of the set: all of it while small, else a sample by weight."""
        word = "dump" if self._size <= SAMPLE_STATES else "sample"
        _, rows = self.helper.ask(f"{word} {SAMPLE_STATES}", time.monotonic() + ANSWER_SECONDS)
        states, weights = [], []
        for row in rows:
            _, weight, fen = row.split(" ", 2)
            states.append(FowBoard(fen))
            weights.append(float(weight))
        if not states:
            raise HelperError("the helper has no states")
        self.states, self._weights = states, weights
        self.uniform_states = []
        if word == "sample":
            # a second sample with equal odds: the king-safety scan looks at both, since the
            # weights can rate the true position too unlikely to be drawn
            _, rows = self.helper.ask(f"usample {UNIFORM_STATES}", time.monotonic() + ANSWER_SECONDS)
            self.uniform_states = [FowBoard(row.split(" ", 2)[2]) for row in rows]

    def _load(self, belief: Belief) -> None:
        """Hand the helper the states of a Python belief. They are a guess, never the full set."""
        rows = [f"s {weight!r} {state.fen(en_passant='fen')}"
                for state, weight in zip(belief.states, belief.weights, strict=True)]
        self._ok("\n".join([f"load 0 {int(belief.weighted)} {len(rows)}", *rows]))

    # -- the parts Belief still does ------------------------------------------------------

    def _as_belief(self, max_states: int = FALLBACK_STATES) -> Belief:
        """A Python belief holding what Python has of the set."""
        belief = Belief(self.side, max_states, self.rng)
        belief.states, belief._weights = list(self.states), list(self.weights)
        belief.weighted = self.weighted
        # Exact only if these are all the states there are, not a sample of them.
        belief.exact = self.exact and len(self.states) == self._size
        belief._started = self._started
        return belief

    def _rebuild(self, obs: str, to_move: chess.Color) -> None:
        """No state fits the observation: project the ones we have onto it (Belief.repair)."""
        belief = self._as_belief()
        belief.repair(obs, to_move)
        self.repairs += 1
        self._load(belief)

    def _top_up(self, obs: str) -> None:
        """A sampled set has grown thin: widen it (Belief.replenish)."""
        _, rows = self.helper.ask(f"dump {MIN_POOL}", time.monotonic() + ANSWER_SECONDS)
        belief = Belief(self.side, FALLBACK_STATES, self.rng)
        belief.states = [FowBoard(row.split(" ", 2)[2]) for row in rows]
        belief._weights = [float(row.split(" ", 2)[1]) for row in rows]
        belief.weighted, belief.exact, belief._started = self.weighted, False, True
        before = len(belief.states)
        belief.replenish(obs)
        if len(belief.states) > before:
            self._load(belief)

    def _fall_back(self, reason: str) -> None:
        """The helper is lost: from here on the set is a Python belief, started from what
        Python last saw of it."""
        self.failure = reason
        self.helper.kill()
        self.fallback = self._as_belief()
        self._mirror()

    def _mirror(self) -> None:
        belief = self.fallback
        self.states, self._weights = belief.states, belief.weights
        self.weighted, self.exact = belief.weighted, belief.exact
        self.max_states, self.update_cost = belief.max_states, belief.update_cost
