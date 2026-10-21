#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/preview-common.sh"
ensure_local_postgres
cd "$ROOT"
(cd backend && "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
api_pid=$!
cleanup() { kill "$api_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
pnpm dev --host 0.0.0.0 --port 3000 --strictPort
