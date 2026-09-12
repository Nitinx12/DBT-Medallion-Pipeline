"""Backward compat shim — use scripts/python/health_check.py."""

import warnings

warnings.warn(
    "scripts/health_check.py is deprecated, use scripts/python/health_check.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.health_check import *
