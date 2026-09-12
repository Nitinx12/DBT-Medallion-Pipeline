"""Backward compat shim — use scripts/python/security_check.py."""

import warnings

warnings.warn(
    "scripts/security_check.py is deprecated, use scripts/python/security_check.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.security_check import *
