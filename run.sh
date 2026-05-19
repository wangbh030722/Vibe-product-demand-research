#!/usr/bin/env bash
# 真需求/伪需求研判 App — one-shot launcher.
#
# Usage:
#     ./run.sh
#     PORT=9000 ./run.sh
#     ANTHROPIC_API_KEY=sk-ant-... ./run.sh
#
# No pip install required for the base app. Install `anthropic` if you want
# the LLM-driven analysis panels:
#     pip install anthropic
set -euo pipefail

PORT="${PORT:-8123}"
HOST="${HOST:-127.0.0.1}"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "[run.sh] WARNING: ANTHROPIC_API_KEY not set. LLM-driven panels will be skipped."
  echo "[run.sh]          Raw VOC collection (Reddit + HN) will still work."
else
  echo "[run.sh] ANTHROPIC_API_KEY detected."
fi

URL="http://${HOST}:${PORT}/"
echo "[run.sh] starting server on ${URL}"

# Try to open the browser ~2s after server starts (macOS / Linux)
(sleep 2 && (open "${URL}" 2>/dev/null || xdg-open "${URL}" 2>/dev/null || true)) &

exec python3 app.py --host "${HOST}" --port "${PORT}"
