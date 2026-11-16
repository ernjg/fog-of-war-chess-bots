#!/bin/bash
# eBotI with checks and captures made likelier in the opponent model, for comparisons.
set -euo pipefail
cd "$(dirname "$0")/../eBotI"
exec "${PYTHON:-python3}" -u bot.py --check-boost 3 --capture-boost 1.5 "$@"
