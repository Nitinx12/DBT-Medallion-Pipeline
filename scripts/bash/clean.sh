#!/usr/bin/env bash
# scripts/bash/clean.sh — housekeeping (mirrors Makefile `clean` / `clean-venv`)
# Usage: scripts/bash/clean.sh [--venv] [--deep]
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/bash/clean.sh [--venv] [--deep]

  (no args)  remove caches + dbt artifacts (keeps .venv)
  --venv     also remove .venv (next run needs uv sync)
  --deep     also remove logs/*, gx/uncommitted/data_docs, __pycache__
  --help     this help
EOF
}

DO_VENV=0; DO_DEEP=0
for arg in "$@"; do
  case "$arg" in
    --venv) DO_VENV=1 ;;
    --deep) DO_DEEP=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; usage; exit 2 ;;
  esac
done

echo "${BOLD}── Clean ──${RESET}"
rm -rf .pytest_cache .ruff_cache .mypy_cache
find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf walmart_dbt/target walmart_dbt/logs walmart_dbt/dbt_packages
rm -rf gx/uncommitted/data_docs 2>/dev/null || true

if [[ $DO_DEEP -eq 1 ]]; then
  echo "Deep clean: __pycache__, logs, .ruff_cache..."
  rm -rf logs/*.log 2>/dev/null || true
  rm -rf .venv_old 2>/dev/null || true
fi

if [[ $DO_VENV -eq 1 ]]; then
  echo "${YELLOW}Removing .venv...${RESET}"
  rm -rf .venv
  echo "Note: on Windows, a locked .venv may need the owning process closed first."
fi

echo "Clean done."
