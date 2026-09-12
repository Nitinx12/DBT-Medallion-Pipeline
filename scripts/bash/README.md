# `scripts/bash/` — Bash helpers (detailed)

Bash complements of the Python pipeline. Every script is `set -euo pipefail`, has `--help`, and is safe to `chmod +x`.

| Script | Purpose | Mirrors |
|---|---|---|
| `preflight.sh` | Env & dependency preflight (Python, uv, .env, pyspark 3.5.x, schemas) | `Makefile: preflight`, `pipeline/run_pipeline.ps1` Stage 0 |
| `extract.sh` | Thin wrapper for `scripts/python/extract.py` (`--tables`, `--full-refresh`, `--dry-run`) | `Makefile: extract` |
| `run_tests.sh` | `bronze\|silver\|gold\|all` via `scripts/python/sql_test.py` | `Makefile: test-bronze/silver/gold`, `ci.yml: integration` |
| `run_pipeline.sh` | **Full 8-stage pipeline** (Linux/macOS mirror of `run_pipeline.ps1`): preflight → extract → bronze tests → dbt silver → silver tests → dbt gold → gold tests → GX | `pipeline/run_pipeline.ps1`, `Makefile: data-pipeline` |
| `health_check.sh` | Shell disk/port checks + delegates to `scripts/python/health_check.py` | `scripts/python/health_check.py` |
| `security_check.sh` | gitleaks (if present) + `.env` not tracked + delegates to `scripts/python/security_check.py` | `scripts/python/security_check.py` |
| `setup_env.sh` | One-shot `uv venv` + `.env` from `.env.example` + hooks + `dbt deps` | `docs: setup` |
| `clean.sh` | Caches & artifacts (`--venv` also removes `.venv`, `--deep` also logs) | `Makefile: clean` |
| `monitor_logs.sh` | Log tail, rotation, and pipeline log analysis (v2, 10k+ lines) | `logs/` |

**Usage:**

```bash
bash scripts/bash/preflight.sh --strict
bash scripts/bash/extract.sh --tables orders,customers --dry-run
bash scripts/bash/run_tests.sh all
bash scripts/bash/run_pipeline.sh --full-refresh
bash scripts/bash/health_check.sh --quick
bash scripts/bash/security_check.sh
bash scripts/bash/setup_env.sh
bash scripts/bash/clean.sh --deep --venv
bash scripts/bash/monitor_logs.sh --follow
```

All scripts respect `PROJECT_ROOT` auto-detection, `PYTHONPATH`, and `.env` loading via `set -a; source .env`.
