#!/usr/bin/env bash
# scripts/bash/health_check.sh — shell wrapper for scripts/python/health_check.py
# Also does shell-level checks (disk, ports) before delegating to Python for DB/Spark checks.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

BOLD="$(tput bold 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/bash/health_check.sh [--quick]

--quick   skip heavy checks (Spark session creation, docker ps)
EOF
}

QUICK=""
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
if [[ "${1:-}" == "--quick" ]]; then QUICK="--quick"; fi

echo "${BOLD}── Health check (shell + python) ──${RESET}"

# Shell checks
echo "Disk usage:"
df -h . | tail -1 | awk '{print "  " $1 " " $3 "/" $2 " (" $5 " used)"}'
# Warn if disk >85%
USE_PCT="$(df -h . | tail -1 | awk '{print $5}' | tr -d '%')"
if [[ "$USE_PCT" -gt 85 ]]; then
  echo "${YELLOW}⚠ Disk usage ${USE_PCT}% >85%${RESET}" >&2
fi

# Ports (best-effort)
for port in 5432 27017 8080; do
  if command -v ss >/dev/null 2>&1; then
    ss -tlnH 2>/dev/null | grep -q ":$port " && echo "Port $port: ${GREEN}listening${RESET}" || echo "Port $port: not listening"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -tln 2>/dev/null | grep -q ":$port " && echo "Port $port: ${GREEN}listening${RESET}" || echo "Port $port: not listening"
  fi
done

echo ""
# Delegate to Python for Postgres/Mongo/Spark/Docker/Airflow checks (rich output)
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
if [[ -n "$QUICK" ]]; then
  exec uv run python scripts/python/health_check.py --quick
else
  exec uv run python scripts/python/health_check.py
fi
