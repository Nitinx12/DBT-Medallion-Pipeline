#!/usr/bin/env bash
# scripts/db_shell.sh — one-shot psql into the warehouse using .env credentials
# Usage: scripts/db_shell.sh [--schema bronze|silver|gold] [-- <psql args>]
# Examples:
#   scripts/db_shell.sh
#   scripts/db_shell.sh --schema gold
#   scripts/db_shell.sh -- -c '\dt gold.*'
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: scripts/db_shell.sh [--schema bronze|silver|gold] [-- <psql args>]"
  exit 0
fi

command -v psql >/dev/null 2>&1 || { echo "psql not found — install PostgreSQL client tools" >&2; exit 1; }
if [[ -f .env ]]; then set -a; source .env; set +a; fi
: "${POSTGRES_HOST:?POSTGRES_HOST missing (.env)}"
: "${POSTGRES_PORT:?POSTGRES_PORT missing (.env)}"
: "${POSTGRES_DATABASE:?POSTGRES_DATABASE missing (.env)}"
: "${POSTGRES_USERNAME:?POSTGRES_USERNAME missing (.env)}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD missing (.env)}"
export PGPASSWORD="$POSTGRES_PASSWORD"

if [[ "${1:-}" == "--schema" ]]; then
  [[ -n "${2:-}" ]] || { echo "--schema needs a value" >&2; exit 2; }
  case "$2" in
    bronze|silver|gold|public) ;;
    *) echo "unknown schema: $2" >&2; exit 2 ;;
  esac
  # PGOPTIONS keeps the session interactive (unlike psql -c).
  export PGOPTIONS="-c search_path=$2,public"
  shift 2
fi
[[ "${1:-}" == "--" ]] && shift

# Password comes from PGPASSWORD so it never appears in `ps` output.
exec psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
  -d "$POSTGRES_DATABASE" "$@"
