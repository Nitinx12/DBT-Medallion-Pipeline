#!/usr/bin/env bash
# scripts/bash/extract.sh — [1/7] Thin wrapper around scripts/python/extract.py
# Passes all args through, ensures PYTHONPATH, and mirrors Makefile `extract`.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

usage() {
  cat <<'EOF'
Usage: scripts/bash/extract.sh [extract.py options]

Wraps: uv run python scripts/python/extract.py

Options (from extract.py):
  --tables <list>              comma-separated collections (default: auto-discover)
  --full-refresh               ignore watermarks, truncate & reload
  --dry-run                    no writes
  --watermark-column <name>    force watermark column for all collections

Examples:
  scripts/bash/extract.sh
  scripts/bash/extract.sh --tables orders,customers
  scripts/bash/extract.sh --full-refresh
  scripts/bash/extract.sh --dry-run
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

exec uv run python scripts/python/extract.py "$@"
