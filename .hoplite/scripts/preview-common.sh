#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCAL="$ROOT/.hoplite/local/w7"
PG_BIN="${HELIX_LOCAL_PG_BIN:-/usr/lib/postgresql/16/bin}"
mkdir -p "$LOCAL"
chmod 700 "$LOCAL"
if [ -x "$ROOT/backend/venv/bin/python" ]; then
  PYTHON="$ROOT/backend/venv/bin/python"
elif [ -x /tmp/w4-venv/bin/python ]; then
  PYTHON=/tmp/w4-venv/bin/python
else
  python3 -m venv "$ROOT/backend/venv"
  PYTHON="$ROOT/backend/venv/bin/python"
  "$PYTHON" -m pip install -r "$ROOT/backend/requirements.txt"
fi
export PYTHON
# This stack always uses its own loopback cluster, never an injected database URL.
export DATABASE_URL='postgresql+asyncpg://helix_w7_api@127.0.0.1:55435/helix_w7_preview'
export TEST_DATABASE_URL='postgresql+asyncpg://postgres@127.0.0.1:55435/helix_w7_preview'
export ENVIRONMENT=development USE_MOCKS=false AUTH_DEV_RESET_RETURN=false
export VITE_DATA_SOURCE=api VITE_API_BASE_URL=/api
export PUBLIC_API_BASE_URL=/api
export PUBLIC_APP_BASE_URL=http://localhost:3000 APP_BASE_URL=http://localhost:3000
export HELIX_DISPATCH_INLINE=false
export VITE_ENABLE_EXPERIMENTAL_FEATURES=false
export BACKEND_CORS_ORIGINS='http://localhost:3000,http://127.0.0.1:3000'
export HELIX_LOCAL_CREDENTIALS="$LOCAL/preview-credentials.json"
if [ ! -f "$HELIX_LOCAL_CREDENTIALS" ]; then
  "$PYTHON" - <<'PY'
import json, os, secrets
from cryptography.fernet import Fernet
path = os.environ['HELIX_LOCAL_CREDENTIALS']
with open(path, 'x') as handle:
    json.dump({'password': secrets.token_urlsafe(24), 'secret_key': secrets.token_urlsafe(48), 'credential_key': Fernet.generate_key().decode()}, handle)
os.chmod(path, 0o600)
PY
fi
SECRET_KEY="$(python3 -c 'import json,os; print(json.load(open(os.environ["HELIX_LOCAL_CREDENTIALS"]))["secret_key"])')"
CREDENTIAL_ENCRYPTION_KEY="$(python3 -c 'import json,os; print(json.load(open(os.environ["HELIX_LOCAL_CREDENTIALS"]))["credential_key"])')"
export SECRET_KEY CREDENTIAL_ENCRYPTION_KEY
# Never inherit production integrations into this provider-free preview.
for key in RENDER METAPI_API_KEY METAPI_KEY METAPI_TOKEN Meta_Api META_API meta_api ADYNTEL_API_KEY ADYNTEL_EMAIL APIFY_API_TOKEN APIFY_TOKEN META_ACCESS_TOKEN BRIGHTDATA_API_KEY SCRAPEGRAPH_API_KEY GROQ_API_KEY OPENROUTER_API_KEY AIHUBMIX_API_KEY TOKENHARBOR_API_KEY GEMINI_API_KEY POLLINATIONS_API_KEY RESEND_API_KEY RESEND_FROM R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET R2_PUBLIC_BASE_URL R2_ENDPOINT_URL NEON_AUTH_URL NEON_AUTH_BASE_URL NEON_JWKS_URL NEON_AUTH_JWKS_URL NEON_JWT_ISSUER NEON_JWT_AUDIENCE NEON_WEBHOOK_SECRET VITE_NEON_AUTH_URL VITE_NEON_AUTH_BASE_URL VITE_MEDIA_BASE_URL VITE_PUBLIC_API_URL CRON_SECRET SCRAPLING_PROXY_LIST SCRAPLING_WORKER_URL; do
  unset "$key"
done
export APIFY_ENABLED=false SCRAPLING_WORKER_ENABLED=false SCRAPLING_INLINE_WORKER=false
pg_run() {
  if [ "$(id -u)" -eq 0 ]; then runuser -u postgres -- "$@"; else "$@"; fi
}
ensure_local_postgres() {
  test -x "$PG_BIN/initdb" || { echo 'PostgreSQL 16 local binaries are required.' >&2; return 1; }
  PG_DATA="$LOCAL/postgres"
  if [ "$(id -u)" -eq 0 ]; then
    chmod 711 "$LOCAL"
    install -d -m 700 -o postgres -g postgres "$PG_DATA"
  else
    mkdir -p "$PG_DATA"
    chmod 700 "$PG_DATA"
  fi
  if [ ! -f "$PG_DATA/PG_VERSION" ]; then pg_run "$PG_BIN/initdb" -D "$PG_DATA" -A trust > "$LOCAL/postgres-init.log"; fi
  if ! pg_run "$PG_BIN/pg_ctl" -D "$PG_DATA" status >/dev/null 2>&1; then
    pg_run "$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$PG_DATA/server.log" -o "-p 55435 -h 127.0.0.1 -k $PG_DATA" start
  fi
  psql -h127.0.0.1 -p55435 -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
SELECT 'CREATE ROLE helix_w7_api LOGIN NOSUPERUSER NOBYPASSRLS INHERIT'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'helix_w7_api')\gexec
SELECT 'CREATE DATABASE helix_w7_preview'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'helix_w7_preview')\gexec
SQL
}
