#!/usr/bin/env bash
# scripts/bash/run_pipeline.sh — Full 8-stage pipeline for Linux/macOS (bash mirror of pipeline/run_pipeline.ps1)
# Stages (strict order, fails fast):
#   0 preflight → 1 extract → 2 bronze tests → 3 dbt silver → 4 silver tests → 5 dbt gold → 6 gold tests → 7 GX
# Exit codes: 0 all passed, 1 stage failed, 2 usage/infra error.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Load .env if present
if [[ -f .env ]]; then set -a; source .env; set +a; fi
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export PYTHONIOENCODING="utf-8"

BOLD="$(tput bold 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/bash/run_pipeline.sh [--dry-run] [--full-refresh] [--tables <list>]

Runs the 8 stages in order, stopping on first failure (same gate as run_pipeline.ps1 and Airflow DAG).

Options forwarded to extract stage:
  --dry-run                  extract --dry-run (no writes)
  --full-refresh             extract --full-refresh
  --tables <list>            extract --tables <list>
  --help                     this help

Examples:
  scripts/bash/run_pipeline.sh
  scripts/bash/run_pipeline.sh --dry-run
  scripts/bash/run_pipeline.sh --tables orders,customers --full-refresh
EOF
}

EXTRACT_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --help|-h) usage; exit 0 ;;
    --dry-run|--full-refresh) EXTRACT_ARGS+=("$arg") ;;
    --tables) EXTRACT_ARGS+=("$arg") ;;
    --tables=*) EXTRACT_ARGS+=("$arg") ;;
    *) EXTRACT_ARGS+=("$arg") ;;
  esac
done

stage() {
  local n="$1"; local name="$2"; shift 2
  echo ""
  echo "${BOLD}════════════════════════════════════════════════════════════${RESET}"
  echo "${BOLD} STAGE $n/7 — $name${RESET}"
  echo "${BOLD}════════════════════════════════════════════════════════════${RESET}"
  if "$@"; then
    echo "${GREEN}✔ Stage $n ($name) passed${RESET}"
  else
    local code=$?
    echo "${RED}✖ Stage $n ($name) failed (exit $code) — stopping pipeline${RESET}" >&2
    exit 1
  fi
}

trap 'echo "${RED}Pipeline interrupted${RESET}" >&2; exit 1' INT TERM

stage "0" "PREFLIGHT" bash scripts/bash/preflight.sh
stage "1" "EXTRACT (Mongo → bronze)" uv run python scripts/python/extract.py "${EXTRACT_ARGS[@]}"
stage "2" "BRONZE SQL TESTS" uv run python scripts/python/sql_test.py tests/bronze
stage "3" "DBT SILVER" bash -c 'cd dbt && uv run dbt run --select silver && uv run dbt test --select silver'
stage "4" "SILVER SQL TESTS" uv run python scripts/python/sql_test.py tests/silver
stage "5" "DBT GOLD" bash -c 'cd dbt && uv run dbt run --select gold && uv run dbt test --select gold'
stage "6" "GOLD SQL TESTS" uv run python scripts/python/sql_test.py tests/gold
stage "7" "GREAT EXPECTATIONS" uv run python -m pipeline.data_quality.run --layer all

echo ""
echo "${GREEN}${BOLD}PIPELINE COMPLETE — all 8 stages passed.${RESET}"
