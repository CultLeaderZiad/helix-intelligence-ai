#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash .hoplite/scripts/run-local.sh
