"""Backward compat shim — use scripts/python/seed_demo_db.py."""

import warnings

warnings.warn(
    "scripts/seed_demo_db.py is deprecated, use scripts/python/seed_demo_db.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.seed_demo_db import *
