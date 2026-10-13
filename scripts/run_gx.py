"""Run Great Expectations suites (thin wrapper over gx.run).

Usage:
    uv run python scripts/run_gx.py [--layer {bronze,silver,gold,all}] [--fail-fast]

Exit codes from gx.run: 0 = all passed, 1 = data failures, 2 = build errors.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gx.run import main

if __name__ == "__main__":
    sys.exit(main())
