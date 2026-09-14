#!/usr/bin/env bash
# scripts/bash/setup_env.sh — one-shot dev setup for Linux/macOS (and Git Bash on Windows)
# Idempotent: safe to run multiple times.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

echo "${BOLD}── Setup dev env ──${RESET}"

# 1. .env from .env.example
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "${GREEN}✔ Created .env from .env.example — edit it with real credentials${RESET}"
  else
    echo "${YELLOW}No .env.example — create .env manually${RESET}"
  fi
else
  echo ".env already exists — skipping"
fi

# 2. uv + venv
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — install: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi
if [[ ! -d .venv ]]; then
  echo "Creating .venv..."
  uv venv
fi
echo "Installing deps (uv sync)..."
uv sync

# 3. hooks
echo "Installing git hooks..."
git config core.hooksPath .githooks
if command -v pre-commit >/dev/null 2>&1 || uv run pre-commit --version >/dev/null 2>&1; then
  uv run pre-commit install --hook-type commit-msg --hook-type pre-commit || true
  echo "${GREEN}✔ pre-commit installed${RESET}"
else
  echo "${YELLOW}pre-commit not available — hooks via .githooks only${RESET}"
fi

# 4. dbt deps
if [[ -d dbt ]]; then
  echo "Installing dbt packages..."
  (cd dbt && uv run dbt deps || true)
fi

echo ""
echo "${GREEN}Setup complete.${RESET}"
echo "Next: edit .env, then run: bash scripts/bash/preflight.sh && bash scripts/bash/run_pipeline.sh"
