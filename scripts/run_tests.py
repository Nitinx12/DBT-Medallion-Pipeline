"""Run SQL test suites for any layer (thin wrapper over src/jobs/sql_test.py).

Usage:
    uv run python scripts/run_tests.py [bronze|silver|gold|all]

Exit 1 if any layer fails.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.jobs.sql_test import run_tests
from src.utils.logger import get_logger

log = get_logger("run_tests", console_level=logging.INFO)

LAYERS = ("bronze", "silver", "gold")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SQL test suites.")
    parser.add_argument(
        "layer",
        nargs="?",
        default="all",
        choices=[*LAYERS, "all"],
        help="Which layer to test (default: all).",
    )
    args = parser.parse_args(argv)

    layers = list(LAYERS) if args.layer == "all" else [args.layer]
    failed = False
    for layer in layers:
        log.info(f"--- SQL tests: {layer} ---")
        if run_tests(PROJECT_ROOT / "tests" / "data-quality" / layer, log):
            log.info(f"{layer} passed")
        else:
            log.error(f"{layer} failed")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
