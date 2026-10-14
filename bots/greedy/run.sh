#!/bin/bash
# Entry point used by the arena (run with bash from the ZIP root).
# Local tools set PYTHON to the project's interpreter; the arena uses python3.
set -euo pipefail
cd "$(dirname "$0")"
exec "${PYTHON:-python3}" -u bot.py "$@"
