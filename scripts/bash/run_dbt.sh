#!/usr/bin/env bash
# scripts/bash/run_dbt.sh — [3/7,5/7] Build + test dbt models in dependency order
# Usage: scripts/bash/run_dbt.sh [silver|gold|all]
# Mirrors Makefile dbt-silver / dbt-gold and the Airflow dbt tasks.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT/dbt"

# dbt/profiles.yml lives in the project (moved out of docker/), so point
# dbt at it explicitly instead of depending on ~/.dbt on every machine.
export DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-$PROJECT_ROOT/dbt}"

BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/bash/run_dbt.sh [silver|gold|all]

Order (dbt resolves in-model order via ref() itself):
  deps -> silver run -> silver test -> gold run -> gold test
With 'silver' or 'gold', only that layer's run+test executes.
Exit 1 on first failure.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
LAYER="${1:-all}"

run_one() {
  local layer="$1"
  echo "${BOLD}── dbt run: $layer ──${RESET}"
  if uv run dbt run --select "$layer" && uv run dbt test --select "$layer"; then
    echo "${GREEN}✔ $layer passed${RESET}"
    return 0
  else
    echo "${RED}✖ $layer failed${RESET}" >&2
    return 1
  fi
}

echo "${BOLD}── dbt deps ──${RESET}"
uv run dbt deps

case "$LAYER" in
  silver|gold) run_one "$LAYER" ;;
  all)
    run_one "silver" || exit 1
    run_one "gold" || exit 1
    ;;
  *) echo "unknown layer: $LAYER" >&2; usage; exit 2 ;;
esac
