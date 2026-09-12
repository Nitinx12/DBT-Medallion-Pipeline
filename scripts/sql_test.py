"""Backward compat shim — use scripts/python/sql_test.py."""

import warnings

warnings.warn(
    "scripts/sql_test.py is deprecated, use scripts/python/sql_test.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.sql_test import *
