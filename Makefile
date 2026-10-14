# ==============================================================================
# Walmart Data Pipeline — Makefile
# Production task runner: static checks, unit tests, the 8-stage data
# pipeline, and build/release, all wired through uv.
#
# Portable across Linux/macOS and Windows (cmd.exe, PowerShell, Git Bash):
# no `grep`/`awk`/`rm`/`tput` in recipes — portable equivalents only.
# ==============================================================================

# ---- Environment -------------------------------------------------------------
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

export PYTHONPATH := $(CURDIR)
export PYTHONIOENCODING := utf-8

# NOTE: no `SHELL := /bin/bash` on purpose. The previous hardcode broke every
# target on Windows (Chocolatey make falls back to cmd.exe, where /bin/bash,
# grep, awk, rm, and tput do not exist). Recipes below use only `make` + `uv`
# + `python` + `docker`, which exist on both platforms.
# NOTE: no tput colors on purpose — tput is missing on Windows and printed
# "The system cannot find the path specified." on every invocation.

UV       := uv
PYTHON   := $(UV) run python
DBT_DIR  := dbt
DBT_ARGS := --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)
SRC_DIRS := .
UNIT_DIR := tests/unit
SMOKE_DIR := tests/smoke
# NOTE: no `2>/dev/null` here on purpose — that is sh-only syntax and prints
# "The system cannot find the path specified." under cmd.exe. `||` works in
# both shells; stderr noise on failure is acceptable (the build needs uv anyway).
VERSION  := $(shell $(UV) run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" || echo 0.0.0-dev)

.DEFAULT_GOAL := help

.PHONY: help install install-dev pre-commit-install \
        lint lint-fix format format-check type-check static-checks unit-test smoke-test test ci \
        preflight extract test-bronze dbt-deps dbt-silver test-silver dbt-gold test-gold gx-tests \
        contracts-check contracts-sync contracts-fix-types dashboard-smoke dag-check \
        data-pipeline all build clean clean-venv \
        report-data report report-watch report-clean report-lint

# ---- Help ----------------------------------------------------------------
help: ## Show this help
	$(PYTHON) -c "import re; print('Walmart Data Pipeline - available targets:'); print(''); [print('  ' + a.ljust(18) + ' ' + b) for a, b in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open('Makefile').read(), re.M)]"

# ---- Setup -----------------------------------------------------------------
install: ## Install runtime dependencies
	$(UV) sync --frozen

install-dev: ## Install runtime + dev dependencies (lint/test tools)
	$(UV) sync --frozen --group dev

pre-commit-install: install-dev ## Install git pre-commit hooks
	$(UV) run pre-commit install

# ---- Lint / Format / Type-check --------------------------------------------
lint: ## Lint Python (ruff), SQL (sqlfluff), and validate the dbt project parses
	@echo ">> ruff check"
	$(UV) run ruff check $(SRC_DIRS)
	@echo ">> sqlfluff lint"
	$(UV) run sqlfluff lint $(DBT_DIR)/models sql tests --dialect postgres
	@echo ">> dbt parse (validates the project graph without touching data)"
	$(UV) run dbt parse $(DBT_ARGS) --quiet

lint-fix: ## Auto-fix lint issues where possible
	$(UV) run ruff check --fix $(SRC_DIRS)
	$(UV) run sqlfluff fix $(DBT_DIR)/models sql tests --dialect postgres --force

format: ## Format Python code in place
	$(UV) run ruff format $(SRC_DIRS)

format-check: ## Check formatting without modifying files (CI-safe)
	$(UV) run ruff format --check $(SRC_DIRS)

type-check: ## Static type-check Python with mypy (auto-provisioned via uv; reports pre-existing findings, not in CI gate)
	$(UV) run --group dev --with mypy mypy $(SRC_DIRS)

# type-check is deliberately NOT part of static-checks: the codebase has
# pre-existing mypy findings (missing stubs/annotations), so it reports rather
# than gates. Fix the findings first, then promote it into static-checks/ci.
static-checks: lint format-check ## Run all static checks (no tests, no data movement)

# ---- Unit tests ---------------------------------------------------------
unit-test: ## Run fast unit tests (no live DB/Spark required)
	$(UV) run pytest $(UNIT_DIR) -v

smoke-test: ## Run smoke tests (imports, layout, CLIs, DAGs, live pings)
	$(UV) run pytest $(SMOKE_DIR) -v

test: ## Run the full pytest suite (unit + smoke)
	$(UV) run pytest -v

# ---- CI entrypoint -----------------------------------------------------
ci: static-checks unit-test ## CI entrypoint: static checks + unit tests (safe to run without live infra)

# ---- Contracts ----------------------------------------------------------
contracts-check: ## Detect contract drift without writing (needs live Postgres)
	$(PYTHON) scripts/run_update_contract.py --check-only

contracts-sync: ## Sync row counts, types, and stats into contracts/*.yml (needs live Postgres)
	$(PYTHON) scripts/run_update_contract.py

contracts-fix-types: ## Adopt observed DB types into contracts/*.yml (needs live Postgres)
	$(PYTHON) scripts/run_update_contract.py --fix-types

# ---- Dashboard / DAG gates (mirror CI jobs) -------------------------------
dashboard-smoke: ## Verify dashboard + connection imports resolve (lightweight mirror of the CI dashboard job)
	$(PYTHON) -c "from src.utils.connection import get_postgres_engine, get_databricks_connection; from dashboard.helpers.queries import Filters, get_filter_options, get_kpis; print('dashboard imports OK')"

dag-check: ## Validate Airflow DAGs import with no cycles (needs airflow installed)
	$(PYTHON) -c "from airflow.models import DagBag; bag = DagBag(dag_folder='airflow/dags'); assert not bag.import_errors, bag.import_errors; assert len(bag.dags) > 0, 'no DAGs found'; print('OK -', len(bag.dags), 'DAG(s):', sorted(bag.dags))"

# ---- Data pipeline (8-stage, strict order, fails fast) ----------------------
preflight: ## [0/7] Verify environment/dependency compatibility
	@echo "------------------------------------------------------------"
	@echo " STEP 0 / 7  -  PREFLIGHT (dependency check)"
	@echo "------------------------------------------------------------"
	$(PYTHON) -c "import pyspark; assert pyspark.__version__.startswith('3.5'), f'Incompatible PySpark version: {pyspark.__version__}. Requires 3.5.x'"

extract: ## [1/7] Extract MongoDB collections into Bronze
	@echo "------------------------------------------------------------"
	@echo " STEP 1 / 7  -  EXTRACT (MongoDB to Bronze)"
	@echo "------------------------------------------------------------"
	$(PYTHON) src/jobs/extract.py

test-bronze: ## [2/7] Run Bronze-layer SQL tests
	@echo "------------------------------------------------------------"
	@echo " STEP 2 / 7  -  BRONZE SQL TESTS"
	@echo "------------------------------------------------------------"
	$(PYTHON) src/jobs/sql_test.py tests/data-quality/bronze

dbt-deps: ## Install dbt packages (run after clean, which wipes dbt/dbt_packages)
	$(UV) run dbt deps $(DBT_ARGS)

dbt-silver: ## [3/7] Build + test Silver dbt models (run `make dbt-deps` first if you ran `make clean`)
	@echo "------------------------------------------------------------"
	@echo " STEP 3 / 7  -  DBT SILVER (build and test)"
	@echo "------------------------------------------------------------"
	$(UV) run dbt run $(DBT_ARGS) --select silver
	$(UV) run dbt test $(DBT_ARGS) --select silver

test-silver: ## [4/7] Run Silver-layer SQL tests
	@echo "------------------------------------------------------------"
	@echo " STEP 4 / 7  -  SILVER SQL TESTS"
	@echo "------------------------------------------------------------"
	$(PYTHON) src/jobs/sql_test.py tests/data-quality/silver

dbt-gold: ## [5/7] Build + test Gold dbt models
	@echo "------------------------------------------------------------"
	@echo " STEP 5 / 7  -  DBT GOLD (build and test)"
	@echo "------------------------------------------------------------"
	$(UV) run dbt run $(DBT_ARGS) --select gold
	$(UV) run dbt test $(DBT_ARGS) --select gold

test-gold: ## [6/7] Run Gold-layer SQL tests
	@echo "------------------------------------------------------------"
	@echo " STEP 6 / 7  -  GOLD SQL TESTS"
	@echo "------------------------------------------------------------"
	$(PYTHON) src/jobs/sql_test.py tests/data-quality/gold

gx-tests: ## [7/7] Run Great Expectations across Bronze/Silver/Gold
	@echo "------------------------------------------------------------"
	@echo " STEP 7 / 7  -  GREAT EXPECTATIONS TESTS (Bronze, Silver, Gold)"
	@echo "------------------------------------------------------------"
	$(PYTHON) -m gx.run --layer all

data-pipeline: preflight extract test-bronze dbt-silver test-silver dbt-gold test-gold gx-tests ## Run the full 8-stage data pipeline in strict order
	@echo ""
	@echo "PIPELINE COMPLETE — all 8 stages passed."

# ---- Composite production gate ----------------------------------------
all: ci data-pipeline ## Full production gate: static checks + unit tests + the live 8-stage data pipeline

# ---- Build / Release --------------------------------------------------------
build: ## Build a distributable wheel; also builds a Docker image if the Dockerfile exists
	$(UV) build
	$(PYTHON) -c "import pathlib, subprocess, sys; sys.exit(subprocess.call(['docker', 'build', '-t', 'walmart-pipeline:$(VERSION)', '-f', 'docker/Dockerfile', '.']) if pathlib.Path('docker/Dockerfile').is_file() else print('No docker/Dockerfile found — skipping image build.'))"

# ---- Housekeeping -----------------------------------------------------------
clean: ## Remove caches and generated artifacts (keeps the venv)
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.ruff_cache', '.mypy_cache', 'dbt/target', 'dbt/logs', 'dbt/dbt_packages', 'gx/uncommitted/data_docs']]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"

clean-venv: ## Remove the virtual environment entirely (forces a full uv sync next run)
	$(PYTHON) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"
	@echo "Note: on Windows, a locked .venv (e.g. an active dbt shell or VS Code kernel) may need that process closed first, or an elevated terminal."

# ---- Technical report (LaTeX, XeLaTeX) ------------------------------------
# -cd keeps font/style paths resolving from reports/ on every platform.
REPORT_TEX := main.tex $(wildcard reports/chapters/*.tex)

report-data: ## Regenerate CSVs for report charts
	$(PYTHON) reports/scripts/collect_metrics.py

report: report-data ## Build reports/build/main.pdf (writes buildmeta, then latexmk)
	$(PYTHON) reports/scripts/write_buildmeta.py
	latexmk -xelatex -cd -outdir=build reports/main.tex

report-watch: ## Live-rebuild the report on save
	latexmk -xelatex -cd -pvc -outdir=build reports/main.tex

report-clean: ## Remove LaTeX build artefacts
	latexmk -cd -C -outdir=build reports/main.tex

# -n12/-n36 are off below: dots and parens inside \file{} paths and code
# listings are not prose abbreviations (chktex cannot see that).
# -n6/-n11/-n15/-n17/-n18/-n25/-n26/-n32/-n37 are off: chktex lints code
# listings and \cmd{...} contents as prose (quotes, parens, ellipsis in
# SQL/Python). Prose typography was reviewed by hand instead.
report-lint: ## chktex style checks over the report sources
	cd reports && chktex -q -n1 -n6 -n8 -n11 -n12 -n13 -n15 -n17 -n18 -n24 -n25 -n26 -n32 -n36 -n37 $(REPORT_TEX:reports/%=%)
