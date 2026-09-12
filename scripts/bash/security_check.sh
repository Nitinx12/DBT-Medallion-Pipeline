#!/usr/bin/env bash
# scripts/bash/security_check.sh — wrapper for scripts/python/security_check.py
# Adds shell-level secret scanning (gitleaks if present) before Python checks.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

echo "${BOLD}── Security check ──${RESET}"

# 1. gitleaks if installed
if command -v gitleaks >/dev/null 2>&1; then
  echo "Running gitleaks..."
  if gitleaks detect --no-git -v 2>&1 | head -20; then
    echo "${GREEN}gitleaks: no leaks detected${RESET}"
  else
    echo "${RED}gitleaks found potential leaks — see above${RESET}" >&2
    exit 1
  fi
else
  echo "${YELLOW}gitleaks not installed — skipping (install: https://github.com/gitleaks/gitleaks)${RESET}"
fi

# 2. quick .env leak guard (never commit .env)
if git ls-files --cached | grep -qx ".env" 2>/dev/null; then
  echo "${RED}✖ .env is tracked by git — should be ignored!${RESET}" >&2
  exit 1
else
  echo "${GREEN}✔ .env not tracked${RESET}"
fi

# 3. Python checks (pattern scan + sensitive file audit)
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
exec uv run python scripts/python/security_check.py
