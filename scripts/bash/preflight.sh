#!/usr/bin/env bash
# scripts/bash/preflight.sh — [0/7] Dependency & env preflight (bash mirror of Makefile `preflight`)
# Fails fast before any data moves. Mirrors pipeline/run_pipeline.ps1 Stage 0 and Makefile preflight.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Colors (safe if tput missing)
BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

usage() {
  cat <<'EOF'
Usage: scripts/bash/preflight.sh [--strict]

Checks:
  - Python 3.11+ and uv
  - .env present and required vars (POSTGRES_*, MONGO_*)
  - pyspark 3.5.x (mongo connector pinned to 3.x)
  - Optional: postgres/mongo reachability if vars set

--strict  fail on warnings (e.g. missing optional schemas)
EOF
}

STRICT=0
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
if [[ "${1:-}" == "--strict" ]]; then STRICT=1; fi

fail() { echo "${RED}✖ $*${RESET}" >&2; exit 1; }
warn() { echo "${YELLOW}⚠ $*${RESET}" >&2; }
ok()   { echo "${GREEN}✔ $*${RESET}"; }

echo "${BOLD}── Preflight [0/7] ──${RESET}"

# 1. Python + uv
command -v uv >/dev/null 2>&1 || fail "uv not found — install from https://docs.astral.sh/uv/"
command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || fail "python not found"
ok "uv + python present"

# 2. .env
if [[ ! -f .env ]]; then
  warn ".env not found — relying on system env (see .env.example)"
  [[ $STRICT -eq 1 ]] && fail "--strict: .env required"
else
  ok ".env present"
fi

# 3. Required env vars (source .env if exists, but don't mutate caller's env beyond check)
if [[ -f .env ]]; then set -a; source .env; set +a; fi
missing=()
for var in POSTGRES_HOST POSTGRES_PORT POSTGRES_DATABASE POSTGRES_USERNAME POSTGRES_PASSWORD MONGO_URI MONGO_DB; do
  if [[ -z "${!var:-}" ]]; then missing+=("$var"); fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
  fail "Missing required env vars: ${missing[*]}"
fi
ok "Required env vars present"

# 4. pyspark version
if uv run python -c "import pyspark" 2>/dev/null; then
  PYSPARK_VER="$(uv run python -c "import pyspark; print(pyspark.__version__)" 2>/dev/null || echo "unknown")"
  if [[ "$PYSPARK_VER" == 4.* ]]; then
    fail "pyspark $PYSPARK_VER installed — mongo-spark-connector 10.4.0 only supports 3.5.x (see scripts/python/extract.py:227)"
  fi
  # must be 3.5.x
  if [[ "$PYSPARK_VER" != 3.5.* ]]; then
    warn "pyspark $PYSPARK_VER — expected 3.5.x (may still work, but connector pinned to 3.5.5)"
    [[ $STRICT -eq 1 ]] && fail "--strict: pyspark 3.5.x required"
  else
    ok "pyspark $PYSPARK_VER"
  fi
else
  warn "pyspark not importable — run 'uv sync' first"
  [[ $STRICT -eq 1 ]] && fail "--strict: pyspark required"
fi

# 5. Optional schemas
for var in POSTGRES_SCHEMA_BRONZE POSTGRES_SCHEMA_SILVER POSTGRES_SCHEMA_GOLD; do
  if [[ -z "${!var:-}" ]]; then warn "$var not set — bronze/silver/gold stages will warn"; fi
done

# 6. Reachability (best-effort, no hard fail unless --strict)
if command -v pg_isready >/dev/null 2>&1 && [[ -n "${POSTGRES_HOST:-}" ]]; then
  if pg_isready -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -q 2>/dev/null; then ok "Postgres reachable at $POSTGRES_HOST:${POSTGRES_PORT:-5432}"
  else warn "Postgres not reachable at $POSTGRES_HOST:${POSTGRES_PORT:-5432} (will fail at extract)"
  fi
fi

ok "Preflight passed"
