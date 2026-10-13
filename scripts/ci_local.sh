#!/usr/bin/env bash
# scripts/ci_local.sh — run the fast CI gates locally (no Docker needed)
# Usage: scripts/ci_local.sh
# Mirrors .github/workflows/ci.yml lint + unit-tests + dbt-parse jobs.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: scripts/ci_local.sh"
  echo "Runs: ruff check, ruff format --check, pytest tests/unit, dbt parse."
  exit 0
fi

gate() {
  local name="$1"; shift
  echo "${BOLD}── $name ──${RESET}"
  if "$@"; then
    echo "${GREEN}✔ $name${RESET}"
  else
    echo "${RED}✖ $name${RESET}" >&2
    exit 1
  fi
}

gate "ruff check" uv run ruff check .
gate "ruff format" uv run ruff format --check .
gate "pytest" uv run pytest tests/unit -q --no-cov
gate "dbt parse" env DBT_PROFILES_DIR="$PROJECT_ROOT/dbt" uv run dbt parse --project-dir dbt --quiet

echo "${GREEN}All local gates passed.${RESET}"
