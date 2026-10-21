#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/preview-common.sh"
ensure_local_postgres
cd "$ROOT/backend"
DATABASE_URL="$TEST_DATABASE_URL" "$PYTHON" -m alembic upgrade head
psql -h127.0.0.1 -p55434 -U postgres -d helix_w6_preview -v ON_ERROR_STOP=1 -c 'GRANT helix_app TO helix_w6_api'
DATABASE_URL="$TEST_DATABASE_URL" PYTHONPATH="$ROOT/backend" "$PYTHON" "$ROOT/.hoplite/scripts/seed-preview.py"
