"""Dashboard smoke gate: ruff check, ruff format check, pytest smoke.

Usage:
    uv run python .claude/skills/dashboard-verify/scripts/smoke_check.py

Exit 0 only when all three gates pass. Works on Windows and Linux.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

GATES: tuple[tuple[str, list[str]], ...] = (
    ("ruff check", [sys.executable, "-m", "ruff", "check", "dashboard"]),
    ("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "dashboard"]),
    ("pytest smoke", [sys.executable, "-m", "pytest", "tests/smoke", "-q", "--no-cov"]),
)


def main() -> int:
    failed = False
    for name, cmd in GATES:
        print(f"--- {name} ---")
        try:
            subprocess.run(cmd, cwd=ROOT, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"FAIL: {name}: {exc}")
            failed = True
    print("smoke_check: " + ("PASS" if not failed else "FAIL"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
