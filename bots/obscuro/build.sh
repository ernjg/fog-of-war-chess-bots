#!/bin/bash
# Arena build step: `bash build.sh` from the ZIP root, 5-minute limit, no network.
#
# Compiles Stockfish from stockfish/src for the bot's Stockfish search (docs/obscuro.md says
# how to put the source there). Unless asked otherwise this script exits 0 whatever happens:
# if Stockfish cannot be built the bot still plays, on its PCFR+ search, and says so in its
# first stderr lines. The last line of this log says which it is:
#
#   build: STOCKFISH OK ...          the bot will use it
#   build: STOCKFISH NOT BUILT ...   the bot will use the PCFR+ search
#
# To have an upload without a working Stockfish rejected instead, put an empty file named
# REQUIRE_STOCKFISH next to this script: the build then fails unless Stockfish works.
#
# For testing: PYTHON sets the interpreter for the start-up check and CPUINFO the file read
# in place of /proc/cpuinfo.

STATUS=0
trap 'exit "$STATUS"' EXIT   # nothing that goes wrong in here may reject the upload by accident
cd "$(dirname "$0")" || exit
[ -e REQUIRE_STOCKFISH ] && STATUS=1   # ... unless that was asked for

SRC=stockfish/src
BIN=$SRC/stockfish
BUILD_UNTIL=250    # seconds from the start: no compiler or linker runs past this
CHECK_UNTIL=275    # and no check of the result past this
JOBS=3             # compilers at once: two cores with four threads, and 4 GiB of memory
PY=${PYTHON:-python3}
CPUINFO=${CPUINFO:-/proc/cpuinfo}
NEED=1             # engines the start-up check must bring up: both, if Stockfish is required
[ "$STATUS" -eq 0 ] || NEED=2
TMP="$PWD/.build-tmp"
LIMITER=none       # what cuts a step off when its time is up: "timeout", where that command exists
WHY=""             # why Stockfish was not built
CHECK=""           # what the check of a good binary reported

say() { echo "build: $*"; }

finish() {  # $1 = the last line of the log, $2 = "ok" if Stockfish works
    rm -rf "$TMP"
    find "$SRC" -name '*.o' -delete 2>/dev/null
    rm -f "$SRC/.depend"
    [ "${2:-}" = ok ] && STATUS=0
    [ "$STATUS" -eq 0 ] || say "REQUIRE_STOCKFISH is present, so this build fails and the upload is rejected"
    say "$1"
    exit "$STATUS"
}

run_for() {  # $1 = seconds, then a command: run it, for at most that long
    local seconds=$1
    shift
    [ "$seconds" -gt 0 ] || return 124
    case "$LIMITER" in
        timeout) timeout -k 5 "$seconds" "$@" ;;
        *)       "$@" ;;
    esac
}

limited() { run_for $((BUILD_UNTIL - SECONDS)) "$@"; }   # a build step

because() {  # $1 = the log of a build step that failed: why it did
    local found=""
    found=$(grep -i 'error\|killed\|terminated' "$1" 2>/dev/null | tail -n 2 | tr '\n' ' ' | cut -c1-300)
    if [ "$SECONDS" -ge "$BUILD_UNTIL" ]; then
        found="the time for building ran out${found:+; $found}"
    elif [ -z "$found" ]; then
        found=$(tail -n 2 "$1" 2>/dev/null | tr '\n' ' ' | cut -c1-300)
    fi
    printf '%s' "${found:-no output}"
}

clean() {
    rm -f "$BIN" "$SRC/.depend"
    find "$SRC" -name '*.o' -delete 2>/dev/null
}

# The binary is good if the bot's own engine code can start it and have every move of the
# starting position scored. A binary built for the wrong CPU dies here.
works() {
    [ -x "$BIN" ] || { WHY="no binary was produced"; return 1; }
    local left=$((CHECK_UNTIL - SECONDS)) answer=""
    [ "$left" -gt 30 ] && left=30
    answer=$(run_for "$left" "$PY" "$TMP/check.py" "$PWD/$BIN" "$NEED" 2> "$TMP/check.err" | tail -n 1 | cut -c1-400)
    case "$answer" in
        "OK "*) CHECK=${answer#OK }; return 0 ;;
        "FAILED "*)
            WHY="the bot's engine code could not use the binary: ${answer#FAILED }"
            return 1 ;;
    esac
    # No answer. If the check said why on stderr it could not run at all (no Python, or
    # engine.py is missing or does not load), and the bot could not use the binary either.
    # If it said nothing it was cut off for time: an earlier check's reason, if any, stands.
    answer=$(tail -n 1 "$TMP/check.err" 2>/dev/null | cut -c1-200)
    if [ -n "$answer" ]; then
        WHY="the bot's own start-up check did not run: $answer"
    elif [ -z "$WHY" ]; then
        WHY="the start-up check gave no answer in the time it had"
    fi
    return 1
}

# Stockfish's own Makefile is not run: calling g++ directly needs no make, compiles in
# parallel and skips the long single-threaded link-time optimisation (worth a few percent
# of speed). The flags are the ones the Makefile passes to g++ 12 on Linux for this ARCH
# (read off `make -n all ARCH=...`), minus link-time optimisation and warnings. With
# NNUE_EMBEDDING_OFF the network file is only read at run time, from beside the binary.
compile() {  # $1 = Stockfish ARCH
    local cxx="" flags="" link="" sources="" sorted="" count=0 objects=0 lane=0 lanes=""
    case "$(uname -s):$1" in
        Darwin:apple-silicon)  # only so this path can be exercised on a Mac
            cxx=clang++
            flags="-flax-vector-conversions=none -fconstexpr-steps=500000000 -arch arm64 -DUSE_POPCNT -DUSE_NEON=8 -march=armv8.2-a+dotprod -DUSE_NEON_DOTPROD"
            link="-m64 -arch arm64 -lpthread" ;;
        Linux:x86-64-avx2)
            flags="-msse -msse3 -mpopcnt -DUSE_POPCNT -DUSE_AVX2 -mavx2 -mbmi -DUSE_SSE41 -msse4.1 -DUSE_SSSE3 -mssse3 -DUSE_SSE2 -msse2" ;;
    esac
    if [ "$(uname -s)" = Linux ]; then
        cxx=g++
        flags="-fno-ipa-cp-clone -fconstexpr-ops-limit=500000000 $flags"
        link="-m64 -Wl,--no-as-needed -lpthread -lrt"
    fi
    command -v "$cxx" >/dev/null 2>&1 || { WHY="$cxx is not installed"; return 1; }
    flags="-std=c++17 -fno-exceptions -DNNUE_EMBEDDING_OFF -m64 -DNDEBUG -O3 -funroll-loops -DIS_64BIT $flags -DARCH=$1"
    sources=$(sed -n '/^SRCS = /,/[^\\]$/p' "$SRC/Makefile" | tr -d '\\\n' | sed 's/^SRCS = //')
    count=$(echo $sources | wc -w | tr -d ' ')
    [ "$count" -gt 0 ] || { WHY="could not read the source list from the Makefile"; return 1; }
    # Largest first, so that no long compile is left to run alone at the end.
    sorted=$(cd "$SRC" && ls -S $sources 2>/dev/null | tr '\n' ' ')
    [ "$(echo $sorted | wc -w | tr -d ' ')" -eq "$count" ] && sources=$sorted
    clean
    rm -rf "$TMP/claims" "$TMP/stop"
    mkdir -p "$TMP/claims"
    say "$cxx, ARCH=$1, $count files, $JOBS at a time ..."
    # Each lane goes down the same list and compiles the files no other lane has taken;
    # making a directory is how a lane takes one, since only one of them can succeed at it.
    while [ "$lane" -lt "$JOBS" ]; do
        lane=$((lane + 1))
        (
            index=0
            for source in $sources; do
                index=$((index + 1))
                [ -e "$TMP/stop" ] && exit 1
                mkdir "$TMP/claims/$index" 2>/dev/null || continue
                ( cd "$SRC" && limited "$cxx" $flags -c -o "$(basename "$source" .cpp).o" "$source" ) \
                    || { : > "$TMP/stop"; exit 1; }
            done
        ) > "$TMP/compile.$lane.log" 2>&1 &
        lanes="$lanes $!"
    done
    wait $lanes
    cat "$TMP"/compile.*.log > "$TMP/manual.log" 2>/dev/null
    objects=$(find "$SRC" -maxdepth 1 -name '*.o' | wc -l | tr -d ' ')
    if [ -e "$TMP/stop" ] || [ "$objects" -ne "$count" ]; then
        WHY="$cxx compiled $objects of $count files: $(because "$TMP/manual.log")"
        return 1
    fi
    if ! ( cd "$SRC" && limited "$cxx" -o stockfish ./*.o $link ) > "$TMP/link.log" 2>&1; then
        WHY="linking failed: $(because "$TMP/link.log")"
        return 1
    fi
}

mkdir -p "$TMP"
export TMPDIR="$TMP"   # compilers write temporaries here; the arena's /tmp is small
clean                  # never keep a binary or objects that came in with the upload

cat > "$TMP/check.py" <<'PY'
# Start the binary the way the bot does and have it score the starting position.
# Prints one line, "OK ..." or "FAILED ...". Anything else means this check did not run.
import importlib.util, os, sys, time
binary, need = sys.argv[1], int(sys.argv[2])
source = next((path for path in ("fow/obscuro/engine.py", "../../fow/obscuro/engine.py")
               if os.path.isfile(path)), None)   # the packaged layout, then the repository's
if source is None:
    sys.exit("fow/obscuro/engine.py is not in the upload")
spec = importlib.util.spec_from_file_location("obscuro_engine", source)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)
began = time.monotonic()
pool = engine.EnginePool.start([binary], 2, began + 8.0, cwd=os.path.dirname(binary))  # as bot.py does
ready, took, scored, depth, search = pool.ready_count(), time.monotonic() - began, 0, None, 0.0
if ready:
    began = time.monotonic()
    result = pool.run([engine.Job("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 12)],
                      began + 5.0, 1.0, 1.0)[0]
    search = time.monotonic() - began
    if result is not None:
        scored, depth = len(result.scores), result.complete_depth(list(result.scores))
why = pool.failure
pool.close()
good = ready >= need and scored == 20 and depth is not None
print(("OK " if good else "FAILED ") + f"{ready} of 2 engines ready in {took:.2f}s, {scored} of 20 "
      f"opening moves scored to depth {depth} in {search:.2f}s" + (f"; {why}" if why else ""))
PY

timeout -k 5 5 true >/dev/null 2>&1 && LIMITER=timeout

# What the sandbox offers, for whoever reads the build log.
if [ "$STATUS" -eq 0 ]; then
    say "REQUIRE_STOCKFISH is absent: this build passes with or without Stockfish"
else
    say "REQUIRE_STOCKFISH is present: this build fails unless Stockfish works (both engines)"
fi
say "$(uname -srm), $(getconf _NPROCESSORS_ONLN 2>/dev/null || echo '?') processors, bash ${BASH_VERSION:-?}"
say "tools: g++=$(command -v g++ || echo none) $PY=$(command -v "$PY" || echo none); steps are cut off by: $LIMITER"
say "compiler: $( (g++ --version 2>/dev/null || c++ --version 2>/dev/null) | head -n 1)"
CPUFLAGS=$(grep -m1 '^flags' "$CPUINFO" 2>/dev/null | cut -d: -f2)
cpu_has() {  # every one of the given CPU flags is present
    local flag
    for flag in "$@"; do
        case " $CPUFLAGS " in
            *" $flag "*) ;;
            *) return 1 ;;
        esac
    done
}
PRESENT=""
for flag in avx2 bmi1 bmi2 popcnt sse4_1 ssse3 avx512f; do
    cpu_has "$flag" && PRESENT="$PRESENT $flag"
done
if [ -n "$CPUFLAGS" ]; then
    say "cpu: $(grep -m1 'model name' "$CPUINFO" 2>/dev/null | cut -d: -f2 | cut -c1-70); of avx2 bmi1 bmi2 popcnt sse4_1 ssse3 avx512f it has:${PRESENT:- none}"
else
    say "cpu: its instruction sets are not known (no flags line in $CPUINFO)"
fi
say "memory: $(grep -m1 MemTotal /proc/meminfo 2>/dev/null | tr -s ' '); space here: $(df -Pk . 2>/dev/null | awk 'NR==2 {print int($4/1024) " MB free"}')"
say "stockfish already installed: $(command -v stockfish || echo no)"

[ -f "$SRC/Makefile" ] || finish "STOCKFISH NOT BUILT: no source in $SRC (docs/obscuro.md says how to fetch it)"
NET=$(grep -o 'nn-[0-9a-f]\{12\}\.nnue' "$SRC/evaluate.h" 2>/dev/null | head -n 1)
[ -n "$NET" ] && [ -f "$SRC/$NET" ] || finish "STOCKFISH NOT BUILT: the network file ${NET:-named in evaluate.h} is not in $SRC"
say "network: $NET, $(wc -c < "$SRC/$NET" | tr -d ' ') bytes"

# One build per platform. The arena's CPU has AVX2; on a CPU without it the binary exits in
# its check and Stockfish is reported as not built.
case "$(uname -s):$(uname -m)" in
    Darwin:arm64) ARCH=apple-silicon ;;
    Linux:x86_64) ARCH=x86-64-avx2 ;;
    *) finish "STOCKFISH NOT BUILT: no build recipe for $(uname -s) $(uname -m)" ;;
esac

# With `timeout` (the arena has it) no build step runs past BUILD_UNTIL and no check past
# CHECK_UNTIL, so the script ends inside the limit.
STARTED=$SECONDS
if compile "$ARCH"; then
    COMPILED=$((SECONDS - STARTED))
    # A first start in a fresh sandbox can be slow, so a failed check is repeated once
    # before the binary is given up.
    if works || { say "  $WHY; checking once more"; works; }; then
        finish "STOCKFISH OK: ARCH=$ARCH, ${COMPILED}s to compile, ${SECONDS}s in all; $CHECK" ok
    fi
fi
clean
finish "STOCKFISH NOT BUILT: $WHY"
