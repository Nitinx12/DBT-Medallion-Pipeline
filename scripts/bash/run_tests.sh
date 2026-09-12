#!/usr/bin/env bash
# scripts/bash/run_tests.sh — [2/7,4/7,6/7] Run SQL test suites for any layer
# Usage: scripts/bash/run_tests.sh [bronze|silver|gold|all]
# Mirrors Makefile test-bronze / test-silver / test-gold and ci.yml integration steps.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/bash/run_tests.sh [bronze|silver|gold|all]

Runs: uv run python scripts/python/sql_test.py tests/<layer>
Exit 1 if any layer fails. With 'all', runs bronze → silver → gold sequentially.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
LAYER="${1:-all}"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

run_one() {
  local layer="$1"
  echo "${BOLD}── SQL tests: $layer ──${RESET}"
  if uv run python scripts/python/sql_test.py "tests/$layer"; then
    echo "${GREEN}✔ $layer passed${RESET}"
    return 0
  else
    echo "${RED}✖ $layer failed${RESET}" >&2
    return 1
  fi
}

case "$LAYER" in
  bronze|silver|gold) run_one "$LAYER" ;;
  all)
    for l in bronze silver gold; do run_one "$l" || exit 1; done
    ;;
  *) echo "unknown layer: $LAYER" >&2; usage; exit 2 ;;
esac
