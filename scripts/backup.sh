#!/usr/bin/env bash
# scripts/backup.sh — Postgres backup & restore for the medallion schemas
# Usage: scripts/backup.sh [backup|restore [file]] [--schema bronze|silver|gold|all]
# Backups land in backups/ (git-ignored) as timestamped custom-format dumps.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/backup.sh [backup|restore [file]] [--schema bronze|silver|gold|all]

  backup           pg_dump the schemas (default: all) into backups/
  restore [file]   pg_restore a dump (default: latest in backups/)
EOF
}

fail() { echo "${RED}✖ $*${RESET}" >&2; exit 1; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
ACTION="${1:-backup}"
SCHEMA="all"
FILE="${2:-}"
for arg in "$@"; do
  case "$arg" in
    --schema=*) SCHEMA="${arg#--schema=}" ;;
  esac
done
case "$SCHEMA" in
  all|bronze|silver|gold) ;;
  *) fail "unknown schema: $SCHEMA" ;;
esac

command -v pg_dump >/dev/null 2>&1 || fail "pg_dump not found — install PostgreSQL client tools"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
: "${POSTGRES_HOST:?POSTGRES_HOST missing (.env)}"
: "${POSTGRES_PORT:?POSTGRES_PORT missing (.env)}"
: "${POSTGRES_DATABASE:?POSTGRES_DATABASE missing (.env)}"
: "${POSTGRES_USERNAME:?POSTGRES_USERNAME missing (.env)}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD missing (.env)}"
export PGPASSWORD="$POSTGRES_PASSWORD"

mkdir -p backups
STAMP="$(date +%Y%m%d_%H%M%S)"
SCHEMA_ARGS=()
[[ "$SCHEMA" != "all" ]] && SCHEMA_ARGS=(-n "$SCHEMA")

if [[ "$ACTION" == "backup" ]]; then
  OUT="backups/${POSTGRES_DATABASE}_${SCHEMA}_${STAMP}.dump"
  echo "${BOLD}── backup $SCHEMA → $OUT ──${RESET}"
  pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
    -F c "${SCHEMA_ARGS[@]}" -f "$OUT" "$POSTGRES_DATABASE"
  echo "${GREEN}✔ backup complete: $OUT${RESET}"
elif [[ "$ACTION" == "restore" ]]; then
  if [[ -z "$FILE" || "$FILE" == --schema* ]]; then
    FILE="$(ls -t backups/*.dump 2>/dev/null | head -n1 || true)"
    [[ -n "$FILE" ]] || fail "no dumps in backups/"
  fi
  [[ -f "$FILE" ]] || fail "dump not found: $FILE"
  echo "${BOLD}── restore $FILE ──${RESET}"
  pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" \
    -d "$POSTGRES_DATABASE" --clean --if-exists "$FILE"
  echo "${GREEN}✔ restore complete${RESET}"
else
  echo "unknown action: $ACTION" >&2; usage; exit 2
fi
