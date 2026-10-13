"""
Run dbt models in dependency order: deps, silver run/test, gold run/test.

dbt resolves in-model order itself via ref() (silver reads
source(bronze, ...), gold refs silver), so the runner only orders layers:

    uv run python src/jobs/run_dbt_models.py [--layer {silver,gold,all}]

Exits 1 on the first failing step. DBT_PROFILES_DIR defaults to the
project's dbt/profiles.yml instead of depending on ~/.dbt.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import get_logger

log = get_logger("run_dbt_models", console_level=logging.INFO)

DBT_DIR = PROJECT_ROOT / "dbt"


def _run_step(description: str, *args: str) -> bool:
    """Run one dbt command, returning True on success."""
    log.info(f"--- dbt {description} ---")
    env = {
        **os.environ,
        "DBT_PROFILES_DIR": os.environ.get("DBT_PROFILES_DIR", str(DBT_DIR)),
    }
    result = subprocess.run(
        ["uv", "run", "dbt", *args], cwd=DBT_DIR, env=env, check=False
    )
    if result.returncode != 0:
        log.error(f"dbt {description} FAILED (exit {result.returncode})")
        return False
    log.info(f"dbt {description} passed")
    return True


def run(layer: str) -> int:
    if not _run_step("deps", "deps"):
        return 1
    for name in ["silver", "gold"] if layer == "all" else [layer]:
        if not _run_step(f"run {name}", "run", "--select", name):
            return 1
        if not _run_step(f"test {name}", "test", "--select", name):
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run dbt models in order.")
    parser.add_argument(
        "--layer",
        choices=["silver", "gold", "all"],
        default="all",
        help="Which layer to build and test (default: all).",
    )
    args = parser.parse_args(argv)
    return run(args.layer)


if __name__ == "__main__":
    sys.exit(main())
