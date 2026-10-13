#!/usr/bin/env bash
set -euo pipefail

REQUIRED_VARS=(POSTGRES_HOST POSTGRES_PORT POSTGRES_DATABASE POSTGRES_USERNAME POSTGRES_PASSWORD)
missing=()
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    missing+=("$var")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "ERROR: missing required environment variable(s): ${missing[*]}" >&2
  exit 1
fi

echo "Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
for i in $(seq 1 30); do
  if (exec 3<>"/dev/tcp/${POSTGRES_HOST}/${POSTGRES_PORT}") 2>/dev/null; then
    exec 3>&- 3<&-
    echo "Postgres is up."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Postgres not reachable after 30 tries." >&2
    exit 1
  fi
  sleep 2
done

exec "$@"
