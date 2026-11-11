#!/usr/bin/env bash
# One command for the browser app: the Python service, the Node API and the page, all on localhost.
set -euo pipefail
cd "$(dirname "$0")/.."
service_port=${RAG_SERVICE_PORT:-8000}
api_port=${RAG_API_PORT:-3001}
ui_port=${RAG_UI_PORT:-5173}

[ -d web/node_modules ] || npm --prefix web ci --silent
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT
trap 'exit 0' INT TERM

uv run uvicorn rag_course.service:create_app --factory --port "$service_port" &
pids=($!)
PORT=$api_port SERVICE_URL=http://127.0.0.1:$service_port npm --prefix web run api &
pids+=($!)
RAG_API_PORT=$api_port npm --prefix web run dev -- --port "$ui_port" --strictPort &
pids+=($!)
echo "Open http://localhost:$ui_port (Ctrl+C stops all three parts)"

# Stop everything when any part exits, and exit with that part's code (never 0: a part should not end by itself).
while true; do
  for pid in "${pids[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      code=0
      wait "$pid" || code=$?
      exit $((code == 0 ? 1 : code))
    fi
  done
  sleep 1
done
