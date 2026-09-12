#!/usr/bin/env bash
# Backward compat shim — use scripts/bash/monitor_logs.sh
echo "WARNING: scripts/monitor_logs.sh is deprecated, use scripts/bash/monitor_logs.sh" >&2
exec "$(dirname "$0")/bash/monitor_logs.sh" "$@"
