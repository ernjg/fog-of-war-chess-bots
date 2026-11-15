# Bot versions

`bots/obscuro` with `fow/obscuro` is the working bot. All new work happens there.

Each version that was uploaded to the arena and differs significantly from the one before
is also kept as a frozen bot of its own. A frozen bot can still be read and played after
the working bot has moved on, so a new idea can always be measured against it.

| Arena version | Bot | Uploaded (UTC) | What it is | Arena record | Source |
| --- | --- | --- | --- | --- | --- |
| 2 | `obscuro_v2` | 2026-11-11 | It keeps a set of possible positions and solves a two-move game over them with PCFR+. Leaves are scored by material and visible squares. It does not use Stockfish. | 210 wins, 19 draws, 331 losses (39%) | Commit `6c25320` |
| 3 | `obscuro_v3` | 2026-11-13 | It adds the Stockfish search. Stockfish scores our moves in up to 64 of the possible positions and the bot plays the best average. The PCFR+ search stays as the fallback. | 32 wins, 4 draws, 40 losses (45%) | Upload ZIP, SHA-256 `f6c4b2bdca0d4053467aef085b8e6b909dfa756a60757920a1b059253066a2a9` |
| 4 | `obscuro_v4` | 2026-11-14 | It adds weights on the possible positions, taken from how Stockfish rates the opponent's moves, and a C++ helper that keeps every possible position. | 158 wins, 12 draws, 92 losses (63%) on 2026-11-15, still live | Upload ZIP, SHA-256 `458eef63afa3ff5cbfcd350c45d4edd411a1ac3553ec1514e8895a0f41383c78` |

The percentage is the score, with a draw counted as half a win.

An arena version without a row was not frozen. It was a fix, a tuning or a second upload
of a frozen bot. Arena version 1 played no games. Version 2 was uploaded two minutes after
it.

`obscuro_v2` loses some local games on time, for example at 30+0.5 and at 36+0.4. It does
not count its belief update against the clock. That was fixed after its upload.

The next version is planned under Next in `docs/obscuro.md`. Its first step is Stockfish
values at the leaves of the PCFR+ tree. It will be built in `bots/obscuro`, with
`obscuro_v4` as the fixed opponent to measure it against.

## What frozen means

A frozen bot is one folder, `bots/obscuro_v<N>`. For v3 and v4 the files beside `bot.py`
are the uploaded bot folder, and the inner folder `obscuro_v<N>` is the uploaded
`fow/obscuro` package, byte for byte. Only the lines that name that package were changed:
7 lines in v3 and 10 in v4. The v2 upload was not kept. `obscuro_v2` is taken in the same
way from commit `6c25320`, the last commit before that upload, with 2 lines changed.

A frozen bot runs only its own code. It shares three things with the working bot:
`fow/__init__.py`, `fow/protocol.py` and the starter kit. A change to any of them changes
every frozen bot as well. The protocol test also runs `obscuro_v3` and `obscuro_v4` with
`tests/fake_uci_engine.py`. If a change to that file breaks those rows, fix the test file
and never the frozen bot.

Frozen bots are never edited, not even to fix a bug. `tests/test_frozen_bots.py` compares
every file with `tests/frozen_bots.sha256` and fails on a changed, added or missing file.
It also fails if a frozen bot loads the working bot's code. To try an idea on an old
version, copy its folder to a new name that does not end in a version number and work on
the copy.

A frozen bot is started through its `run.sh`. Code that loads a frozen `bot.py` by file
path must first put that bot's folder on `sys.path`.

`uv run tools/package.py obscuro_v4` packages a frozen bot once its Stockfish source is in
place (see the next section). The result is a new ZIP that plays the same as the original
upload but is laid out differently. A frozen bot that is uploaded again is not frozen a
second time.

## Playing versions against each other

`obscuro_v3`, `obscuro_v4` and the working bot each need their own Stockfish. A bot without
one plays its older PCFR+ search and does not fail, so a comparison can be wrong without any
error.

1. Fetch the Stockfish source for each bot with that bot's own script. Each fetch needs the
   network and is about 95 MB.

   ```sh
   bash bots/obscuro/fetch_stockfish.sh
   bash bots/obscuro_v3/fetch_stockfish.sh
   bash bots/obscuro_v4/fetch_stockfish.sh
   ```

   All three scripts name the same release today, `sf_19`. While that holds, copying one
   fetched folder gives the same result without another download, for example
   `cp -R bots/obscuro/stockfish bots/obscuro_v3/stockfish`.

2. Build each bot with its own script. Each run must end with `build: STOCKFISH OK`. The
   working bot and `obscuro_v4` also print `build: POSITION SET OK`. On a Mac whose linker
   cannot find the SDK, set `SDKROOT` first as `docs/obscuro.md` describes.

   ```sh
   bash bots/obscuro/build.sh
   bash bots/obscuro_v3/build.sh
   bash bots/obscuro_v4/build.sh
   ```

3. Check that a bot starts its own engines. The line it prints must name a binary inside
   that bot's own folder.

   ```sh
   printf 'fow\nw 180 2\n' | uv run bash bots/obscuro_v4/run.sh 2>&1 >/dev/null | grep "stockfish ready"
   ```

4. Play. Leave `FOW_STOCKFISH` and `FOW_POSITIONS` unset. Every bot that uses Stockfish
   reads the first, and `obscuro_v4` and the working bot read the second, so they would
   all share one binary.

   ```sh
   uv run tools/tournament.py obscuro obscuro_v4 --games 10 --base 36 --inc 0.4
   ```

   These ten games take about a minute each. Without `--base` and `--inc` the games use
   the arena's 180+2 and take several minutes each. More bot names make a round-robin,
   and `--games` is then the number of games per pairing.

One short match says very little. Bots that play identically have finished 30-game matches
here anywhere between 23% and 60% for one side, and results come in streaks, because the
bots repeat a small set of openings. In one afternoon the working bot's code won only 19 of
72 games against `obscuro_v4` in its first three matches and then 62 of 120 in the next
four, although the two are the same program in a normal game. To compare two versions, play
the pairing in both listing orders, at least 60 games each way, and add the results before
reading anything into a difference.

```sh
uv run tools/tournament.py obscuro obscuro_v4 --games 60 --base 36 --inc 0.4
uv run tools/tournament.py obscuro_v4 obscuro --games 60 --base 36 --inc 0.4
```

## Freezing a new version

Freeze a version once it has been uploaded and it differs significantly from the last
frozen one. That means a different search or a different way of tracking positions, not a
fix or tuning. The folder is named after the arena's version number, so it cannot be made
before the upload.

Commit before uploading, and package from that commit. The v3 and v4 uploads were made from
uncommitted trees, which is why no commit matches them.

In these steps `N` is the arena's version number and `C` is the uploaded commit.

1. Copy the tracked files of that commit.

   ```sh
   mkdir -p bots/obscuro_vN/obscuro_vN
   git archive C:bots/obscuro | tar -x -C bots/obscuro_vN
   git archive C:fow/obscuro | tar -x -C bots/obscuro_vN/obscuro_vN
   ```

   If an upload was made from an uncommitted tree after all, take the files from the
   uploaded ZIP instead. Its `fow/obscuro` folder goes to `bots/obscuro_vN/obscuro_vN`. Its
   other files go to `bots/obscuro_vN`, without `fow/`, `referee.py`, `uniform_random.py`
   and `stockfish/`. Write the ZIP's SHA-256 into the table.

2. In the files directly inside `bots/obscuro_vN`, replace `fow.obscuro.` with
   `obscuro_vN.` and `fow/obscuro/` with `obscuro_vN/`. Do not touch the inner folder and
   change nothing else.

   ```sh
   perl -pi -e 's/fow\.obscuro\./obscuro_vN./g' bots/obscuro_vN/*.*
   perl -pi -e 's{fow/obscuro/}{obscuro_vN/}g' bots/obscuro_vN/*.*
   ```

   If `tests/test_frozen_bots.py` still finds the working bot's package afterwards,
   replace that mention by hand in the same way and list those lines in the commit
   message.

3. Record the checksums. Use `sha256sum` where there is no `shasum`.

   ```sh
   git add bots/obscuro_vN
   git ls-files bots/obscuro_vN | xargs shasum -a 256 >> tests/frozen_bots.sha256
   ```

4. Add a row for the bot to `CASES` in `tests/test_protocol.py` and a line to the table at
   the top of this file.

5. Run the tests and commit. `git diff C:fow/obscuro HEAD:bots/obscuro_vN/obscuro_vN` must
   print nothing.

## Checking a frozen bot against its upload

Undoing the two replacements of step 2 gives the original files back byte for byte.

For v2, git can show it. `git diff 6c25320:fow/obscuro HEAD:bots/obscuro_v2/obscuro_v2`
prints nothing, and `git diff 6c25320:bots/obscuro/bot.py HEAD:bots/obscuro_v2/bot.py`
shows the two import lines.

The v3 and v4 uploads are not in git. The commit that added their folders holds the
uploaded files unchanged, and the commit after it shows the changed lines. Anyone who has
an uploaded ZIP can compare a file with it:

```sh
unzip -p obscuro-v4.zip fow/obscuro/belief.py | shasum -a 256
```

The result must equal the line for `bots/obscuro_v4/obscuro_v4/belief.py` in
`tests/frozen_bots.sha256`.
