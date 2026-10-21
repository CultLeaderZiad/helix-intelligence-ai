#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/preview-common.sh"
ensure_local_postgres
cd "$ROOT"
(cd backend && "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
api_pid=$!
web_pid=''
cleanup() {
  kill "$api_pid" ${web_pid:+"$web_pid"} 2>/dev/null || true
}
trap cleanup EXIT INT TERM
ready=false
for attempt in {1..30}; do
  kill -0 "$api_pid" 2>/dev/null || { echo 'Local API exited before readiness.' >&2; exit 1; }
  if curl --fail --silent --max-time 1 http://127.0.0.1:8000/health >/dev/null; then ready=true; break; fi
  sleep 1
done
if [ "$ready" != true ]; then echo 'Local API readiness timed out.' >&2; exit 1; fi
pnpm dev --host 0.0.0.0 --port 3000 --strictPort &
web_pid=$!
wait -n "$api_pid" "$web_pid"
