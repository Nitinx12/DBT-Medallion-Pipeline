"""Smoke: CLI entry points respond to --help with exit 0."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SCRIPTS = [
    ["src/jobs/extract.py", "--help"],
    ["src/jobs/run_dbt_models.py", "--help"],
    ["scripts/run_tests.py", "--help"],
    ["scripts/run_gx.py", "--help"],
    ["scripts/seed_demo_db.py", "--help"],
]


def _run(script_args):
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [
            sys.executable,
            *(str(ROOT / a) if not a.startswith("-") else a for a in script_args),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.parametrize("args", SCRIPTS, ids=[a[0] for a in SCRIPTS])
def test_cli_help_exits_zero(args):
    result = _run(args)
    assert result.returncode == 0, f"{args[0]} --help failed:\n{result.stderr[-2000:]}"
