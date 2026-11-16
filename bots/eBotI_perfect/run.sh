#!/bin/bash
# eBotI with a perfect-information opponent in the tree, for comparisons.
set -euo pipefail
cd "$(dirname "$0")/../eBotI"
exec "${PYTHON:-python3}" -u bot.py --opponent perfect "$@"
