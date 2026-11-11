#!/usr/bin/env bash
# One command for the browser app: the Python service, the Node API and the page, all on localhost.
set -euo pipefail
cd "$(dirname "$0")/.."
service_port=${RAG_SERVICE_PORT:-8000}
api_port=${RAG_API_PORT:-3001}
ui_port=${RAG_UI_PORT:-5173}

[ -d web/node_modules ] || npm --prefix web ci --silent
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM

uv run uvicorn rag_course.service:create_app --factory --port "$service_port" &
PORT=$api_port SERVICE_URL=http://127.0.0.1:$service_port npm --prefix web run api &
RAG_API_PORT=$api_port npm --prefix web run dev -- --port "$ui_port" --strictPort &
echo "Open http://localhost:$ui_port (Ctrl+C stops all three parts)"

# Stop everything when any part exits.
while [ "$(jobs -r | wc -l)" -eq 3 ]; do sleep 1; done
