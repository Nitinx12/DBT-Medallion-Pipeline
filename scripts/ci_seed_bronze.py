"""Backward compat shim — use scripts/python/ci_seed_bronze.py."""

import warnings

warnings.warn(
    "scripts/ci_seed_bronze.py is deprecated, use scripts/python/ci_seed_bronze.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.ci_seed_bronze import *
