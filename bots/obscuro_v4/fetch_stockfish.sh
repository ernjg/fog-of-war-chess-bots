#!/bin/bash
# Put the Stockfish source and its network file in bots/obscuro/stockfish/, where build.sh
# compiles them. Needs the network; run it once before packaging. The folder is gitignored
# (about 100 MB) and travels to the arena inside the ZIP.
#
# Everything is downloaded to stockfish.new first and replaces stockfish/ only once it is
# complete and the network file matches its checksum, so a run that fails leaves whatever
# was there before untouched.
set -euo pipefail
cd "$(dirname "$0")"

TAG=sf_19   # build.sh and obscuro_v4/stockfish_search.py were tested against this release
NEW=stockfish.new

rm -rf "$NEW"
trap 'rm -rf "$NEW"' EXIT
git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$TAG" \
    https://github.com/official-stockfish/Stockfish.git "$NEW"
rm -rf "$NEW/.git" "$NEW/.github"

NET=$(grep -o 'nn-[0-9a-f]\{12\}\.nnue' "$NEW/src/evaluate.h" | head -n 1 || true)
[ -n "$NET" ] || { echo "could not find the network name in $NEW/src/evaluate.h" >&2; exit 1; }
curl -fsSL --retry 2 -o "$NEW/src/$NET" "https://data.stockfishchess.org/nn/$NET" \
    || curl -fsSL --retry 2 -o "$NEW/src/$NET" \
        "https://github.com/official-stockfish/networks/raw/master/$NET" \
    || { echo "could not download $NET" >&2; exit 1; }

# The file name is the first 12 hex digits of the file's SHA-256.
if command -v sha256sum >/dev/null 2>&1; then
    SUM=$(sha256sum "$NEW/src/$NET" | cut -c1-12)
else
    SUM=$(shasum -a 256 "$NEW/src/$NET" | cut -c1-12)
fi
if [ "nn-$SUM.nnue" != "$NET" ]; then
    echo "$NET does not match its checksum (got nn-$SUM.nnue); the download is damaged" >&2
    exit 1
fi

rm -rf stockfish
mv "$NEW" stockfish
trap - EXIT
echo "Stockfish $TAG and $NET ($(wc -c < "stockfish/src/$NET" | tr -d ' ') bytes) are in $PWD/stockfish"
