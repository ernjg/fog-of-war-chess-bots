#!/bin/bash
# eBotI with its depth-2 PCFR+ search, for comparisons (not a bot of its own).
set -euo pipefail
cd "$(dirname "$0")/../eBotI"
exec "${PYTHON:-python3}" -u bot.py --search pcfr "$@"
