"""Stockfish over UCI: a small pool of engine processes, with a deadline on every wait.

The engines are children of the bot and stay in its process group, so whatever pauses
the bot between turns pauses them too. ``EnginePool.run`` returns only once every engine
is idle or dead, so nothing is left searching when the bot answers.

Nothing here can block for long or raise on an engine fault: a process that exits, hangs
or prints nonsense is killed and its job comes back as ``None``.
"""
from __future__ import annotations

import math
import os
import select
import subprocess
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field

CP_SCALE = 600.0       # value = tanh(centipawns / 600), the paper's 6-pawn scale
MAX_CP_VALUE = 0.99    # a centipawn score never reaches a mate score
CP_TAIL = 0.01         # the part of that range that keeps growing with the score ...
CP_LIMIT = 20000.0     # ... up to this many centipawns
MULTIPV = 256          # Stockfish's maximum; no position has more than 218 legal moves
HASH_MB = int(os.environ.get("FOW_HASH", "16"))  # v4: 16
STOP_GRACE = 0.5       # seconds an engine gets to answer "stop" before it is killed
LAST_LOOK = 0.05       # and one more look after that, in case it was us who were not running
MAX_BUFFER = 1 << 20   # an engine holding back this much output without a newline is broken
MAX_RESTARTS = 3       # per game


def cp_value(centipawns: int) -> float:
    """tanh of the score, plus a small term that keeps rising with it. tanh alone is flat
    beyond about 16 pawns: every move of a won position would be worth the same, and the
    bot would shuffle its pieces instead of taking the rook or promoting."""
    tail = max(-1.0, min(1.0, centipawns / CP_LIMIT))
    return (MAX_CP_VALUE - CP_TAIL) * math.tanh(centipawns / CP_SCALE) + CP_TAIL * tail


def mate_value(moves: int) -> float:
    """Mate by the side to move in ``moves`` (> 0), or against it (<= 0); sooner is larger."""
    size = 1.0 - 0.0001 * min(abs(moves), 50)
    return size if moves > 0 else -size


def parse_info(line: str) -> tuple[int, int, str, float] | None:
    """(depth, rank, move, value) from one Stockfish line. With MultiPV, Stockfish prints
    one line per legal move, ranked 1 = best; ``value`` is the move's score for the side to
    move, on the -1..1 scale of ``cp_value`` / ``mate_value``. For example:

        info depth 12 seldepth 18 multipv 2 score cp 30 ... pv d2d4 d7d5
            -> (12, 2, "d2d4", 0.049)

    None for lines whose score is not exact: non-search or malformed lines, unsearched
    placeholders (``seldepth 0`` or an empty ``pv``) and ``lowerbound``/``upperbound``.
    """
    parts = line.split()
    if len(parts) < 10 or parts[0] != "info" or parts[1] != "depth":
        return None
    try:
        depth = int(parts[2])
        if int(parts[parts.index("seldepth", 3) + 1]) < 1:
            return None
        rank = int(parts[parts.index("multipv", 3) + 1])
        at = parts.index("score", 3)
        kind, amount = parts[at + 1], int(parts[at + 2])
        if parts[at + 3] in ("lowerbound", "upperbound"):
            return None
        move = parts[parts.index("pv", at + 3) + 1]
    except (ValueError, IndexError):
        return None
    if kind == "cp":
        return depth, rank, move, cp_value(amount)
    if kind == "mate":
        return depth, rank, move, mate_value(amount)
    return None


@dataclass(frozen=True)
class Job:
    fen: str  # board
    depth: int  # depth to search to


@dataclass
class JobResult:
    scores: dict[str, dict[int, float]]  # move -> depth -> value for the side to move
    no_moves: bool                        # "bestmove (none)": the side to move has no legal move
    stopped: bool                         # cut short by "stop" rather than reaching its depth

    def complete_depth(self, moves: Sequence[str]) -> int | None:
        """Deepest depth at which every one of ``moves`` has a score, so that their
        values compare like with like."""
        depths: set[int] | None = None
        for move in moves:
            found = self.scores.get(move)
            if not found:
                return None
            depths = set(found) if depths is None else depths & found.keys()
            if not depths:
                return None
        return max(depths) if depths else None

    def best(self) -> float | None:
        """Value of the position for the side to move: its best move at the deepest
        depth that covers every move the engine reported."""
        depth = self.complete_depth(list(self.scores))
        if depth is None:
            return None
        return max(found[depth] for found in self.scores.values())


class Engine:
    """One engine process. Every method is safe to call on a dead engine."""

    def __init__(self, command: Sequence[str], cwd: str | None = None):
        self.dead = False
        self.tail: deque[str] = deque(maxlen=3)  # last non-search lines read, for diagnostics
        self._buffer = b""
        # stdout must be our pipe, never the bot's stdout: that one belongs to the referee.
        # No new session or process group: the engine has to be paused together with the bot.
        self.proc = subprocess.Popen(list(command), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, bufsize=0, cwd=cwd)
        self.fd = self.proc.stdout.fileno()
        os.set_blocking(self.fd, False)

    def send(self, text: str) -> bool:
        """Write commands (short, so the pipe never fills) to stockfish; False if the engine is gone."""
        if self.dead:
            return False
        data = text.encode("ascii")
        try:
            while data:
                data = data[os.write(self.proc.stdin.fileno(), data):]
        except (OSError, ValueError):
            self.kill()
            return False
        return True

    def read_lines(self) -> list[str]:
        """The complete lines available right now, about MAX_BUFFER bytes of them at most:
        an engine that never pauses its output must not keep us here. End of file marks
        the engine dead."""
        while not self.dead and len(self._buffer) <= MAX_BUFFER:
            try:
                chunk = os.read(self.fd, 65536)
            except BlockingIOError:
                break
            except (OSError, ValueError):
                self.kill()
                break
            if not chunk:
                self.kill()
                break
            self._buffer += chunk
            if len(chunk) < 65536:
                break
        *done, self._buffer = self._buffer.split(b"\n")
        if len(self._buffer) > MAX_BUFFER:
            self.kill()
        lines = [raw.decode("ascii", "replace").strip() for raw in done]
        # Stockfish states why it is exiting at the end of an "info string" line.
        self.tail.extend(line[-200:] for line in lines if line and not line.startswith("info depth"))
        return lines

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
        """Ask the engine to exit, then make sure it has."""
        if not self.dead:
            self.send("quit\n")
            try:
                self.proc.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        self.kill()


@dataclass
class _Running:
    index: int
    stop_at: float
    kill_at: float = math.inf
    stop_sent: bool = False
    scores: dict[str, dict[int, float]] = field(default_factory=dict)
    block: dict[str, tuple[int, float]] = field(default_factory=dict)  # lines of the newest report
    block_after_stop: bool = False  # whether that report began after we sent "stop"
    looked_again: bool = False

    def read(self, line: str) -> None:
        """Take in one search line. Stockfish reports all moves together after each
        iteration, best first, so a rank 1 line opens a new report, even one that carries
        no usable score (after "stop" it can be a mere bound)."""
        if line.startswith("info depth ") and " multipv 1 " in line:
            self.keep_block()
            self.block_after_stop = self.stop_sent
        parsed = parse_info(line)
        if parsed is not None:
            depth, _, move, value = parsed
            self.block[move] = (depth, value)

    def keep_block(self) -> None:
        """File the finished report under its depths, unless it is the one printed in
        answer to "stop". That one is not an iteration: moves the interrupted iteration
        had not reached carry their old scores, some of them under the new depth."""
        if not self.block_after_stop:
            for move, (depth, value) in self.block.items():
                self.scores.setdefault(move, {})[depth] = value
        self.block = {}

    def result(self, bestmove: str) -> JobResult:
        self.keep_block()
        return JobResult(self.scores, bestmove.split()[1:2] == ["(none)"], self.stop_sent)


class EnginePool:
    def __init__(self, command: Sequence[str], cwd: str | None = None):
        self.command = list(command)
        self.cwd = cwd  # Stockfish looks for its network file here and beside its binary, short for current working directory
        self.engines: list[Engine] = []
        self.wanted = 0
        self.restarts = 0
        self.restart_limit = MAX_RESTARTS
        self.deaths = 0
        self.failure = ""  # why the most recent engine was lost, for the log
        self.start_seconds = 0.0  # what the slowest engine that did start needed, last time

    @classmethod
    def start(cls, command: Sequence[str], count: int, deadline: float,
              cwd: str | None = None) -> "EnginePool":
        """Start ``count`` engines; the ones that are not ready by ``deadline`` are dropped."""
        pool = cls(command, cwd)
        pool.wanted = count
        pool.engines = pool._spawn(count, deadline)
        return pool

    def ready_count(self) -> int:
        return sum(not engine.dead for engine in self.engines)

    def restart(self, deadline: float) -> int:
        """Replace dead engines, within the per-game restart allowance. Returns how many."""
        self.engines = [engine for engine in self.engines if not engine.dead]
        missing = min(self.wanted - len(self.engines), self.restart_limit - self.restarts)
        if missing <= 0:
            return 0
        self.restarts += missing
        fresh = self._spawn(missing, deadline)
        self.engines.extend(fresh)
        return len(fresh)

    def close(self) -> None:
        for engine in self.engines:
            engine.quit()
        self.engines = []

    def _spawn(self, count: int, deadline: float) -> list[Engine]:
        """Start ``count`` engines and take each through the handshake at its own pace,
        so that a slow or silent one does not cost the others their time. The ones that
        have not finished by ``deadline`` are killed."""
        # "uci" lists the options; the search at the end proves the network file loads,
        # which Stockfish only checks at its first "go" (it exits if the file is missing).
        options = (f"setoption name Threads value 1\nsetoption name Hash value {HASH_MB}\n"
                   f"setoption name MultiPV value {MULTIPV}\nisready\n")
        steps = (("uci\n", "uciok"), (options, "readyok"),
                 ("position startpos\ngo depth 1\n", "bestmove"))
        step: dict[Engine, int] = {}  # the step each engine has still to answer, eg {engine_A: 0, engine_B: 0}
        began = time.monotonic()
        for _ in range(count):
            try:
                engine = Engine(self.command, self.cwd)
            except (OSError, ValueError) as error:
                self.failure = f"could not start {self.command[0]}: {error}"
                continue
            if engine.send(steps[0][0]):
                step[engine] = 0
            else:
                self._lost(engine, "exited at once")
        ready: list[Engine] = []
        while step:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                break
            for engine in self._select(list(step), timeout):
                reply = steps[step[engine]][1]
                if any(line.startswith(reply) for line in engine.read_lines()):
                    step[engine] += 1
                    if step[engine] == len(steps):  # all steps completed
                        del step[engine]
                        ready.append(engine)
                        self.start_seconds = time.monotonic() - began
                    elif not engine.send(steps[step[engine]][0]):  # sending fails
                        del step[engine]
                        self._lost(engine, f"exited after {reply}")
                elif engine.dead:
                    del step[engine]
                    self._lost(engine, f"exited while waiting for {reply}")
        for engine, index in step.items():
            self._lost(engine, f"no {steps[index][1]} in time")
            engine.kill()
        return [engine for engine in ready if not engine.dead]

    def run(self, jobs: Sequence[Job], deadline: float, min_slice: float,
            max_slice: float) -> list[JobResult | None]:
        """Search every job, sharing the time left until ``deadline`` between them.

        Each job gets an equal slice of what remains when it starts, between ``min_slice``
        and ``max_slice``, and is told to stop when the slice ends; a stopped search still
        returns the depths it completed. A job is ``None`` if it never ran or its engine
        failed. On return every engine is idle or dead.
        """
        results: list[JobResult | None] = [None] * len(jobs)
        queue = deque(range(len(jobs)))
        running: dict[Engine, _Running] = {}
        while True:
            now = time.monotonic()
            # hand out work
            for engine in self.engines:
                if not queue or now >= deadline:
                    break
                if engine.dead or engine in running:
                    continue
                share = (deadline - now) * max(1, self.ready_count()) / len(queue)  # time left * # engines / # waiting jobs
                index = queue.popleft()
                job = jobs[index]
                if engine.send(f"position fen {job.fen}\ngo depth {job.depth}\n"):
                    slice_seconds = min(max(share, min_slice), max_slice)  # keep share between min_slice and max_slice
                    stop_at = min(now + slice_seconds, deadline)
                    running[engine] = _Running(index, stop_at)
                else:
                    self._lost(engine, "exited before a search")
                    queue.appendleft(index)  # another engine can still take it
            # if queue is empty and no engines are running, we are done
            if not running:
                return results
            # wait and read
            wake = min(state.kill_at if state.stop_sent else state.stop_at
                       for state in running.values())
            ready = self._select(list(running), max(0.0, wake - time.monotonic()))
            for engine in ready:
                state = running[engine]  # current job, which job it is, time limit, and move scores read so far
                for line in engine.read_lines():
                    if line.startswith("bestmove"):  # bestmove line means search is done
                        results[state.index] = state.result(line)
                        del running[engine]
                        break
                    state.read(line)
                else:
                    if engine.dead:
                        self._lost(engine, "exited during a search")
                        del running[engine]
            # enforce time limits, stopping engines that have exceeded their allotted time
            now = time.monotonic()
            for engine, state in list(running.items()):
                if not state.stop_sent and now >= state.stop_at:
                    state.stop_sent, state.kill_at = True, now + STOP_GRACE
                    if not engine.send("stop\n"):
                        self._lost(engine, "exited during a search")
                        del running[engine]
                elif state.stop_sent and now >= state.kill_at:
                    # If it was this process that did not run for a while, the answer may
                    # only just be arriving: look once more before giving up on the engine.
                    if not state.looked_again and self._select([engine], LAST_LOOK):
                        state.looked_again = True
                        state.kill_at = time.monotonic() + LAST_LOOK  # read it next round
                        continue
                    self._lost(engine, "did not answer stop")
                    engine.kill()
                    del running[engine]

    @staticmethod
    def _select(engines: list[Engine], timeout: float) -> list[Engine]:
        """The engines with output (or end of file) to read within ``timeout`` seconds."""
        try:
            readable, _, _ = select.select([engine.fd for engine in engines], [], [], timeout)
        except (OSError, ValueError):
            return list(engines)  # a descriptor went bad: read_lines sorts out which
        return [engine for engine in engines if engine.fd in readable]

    def _lost(self, engine: Engine, why: str) -> None:
        self.deaths += 1
        # Stockfish gives its reason for exiting at the end of its last line: keep the end.
        said = " | ".join(engine.tail) or "(none)"
        self.failure = f"{why}; last output: {said[-260:]}"
