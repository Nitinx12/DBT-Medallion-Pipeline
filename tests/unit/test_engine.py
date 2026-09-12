import importlib
import os
import warnings
from unittest.mock import patch


def _reload_engine(env_overrides: dict):
    """Helper: patch os.environ, remove cached module, reimport."""
    with patch.dict(os.environ, env_overrides, clear=False):
        if "utils.engine" in __import__("sys").modules:
            del __import__("sys").modules["utils.engine"]
        # Also need to clear dotenv cache? load_dotenv only warns, safe to reimport
        import utils.engine as eng

        importlib.reload(eng)
        return eng


def test_postgres_port_cast_to_int():
    """POSTGRES_PORT string is cast to int at import time."""
    eng = _reload_engine({"POSTGRES_PORT": "5433"})
    assert eng.POSTGRES_PORT == 5433
    assert isinstance(eng.POSTGRES_PORT, int)


def test_postgres_port_invalid_raises_oserror():
    """Non-integer POSTGRES_PORT raises OSError on import."""
    import sys

    # Patch int conversion to raise
    try:
        _reload_engine({"POSTGRES_PORT": "not_a_port"})
        assert False, "should have raised OSError"
    except OSError as exc:
        assert "POSTGRES_PORT must be an integer" in str(exc)
    finally:
        # Restore sane state for subsequent tests
        if "utils.engine" in sys.modules:
            del sys.modules["utils.engine"]
        os.environ["POSTGRES_PORT"] = "5432"


def test_missing_required_env_raises():
    """Missing any hard-required var raises OSError listing all missing."""
    import sys

    env_missing = {
        "POSTGRES_HOST": "",
        "MONGO_URI": "",
    }
    # We need to physically unset or set to empty string — engine checks `if not v`
    try:
        with patch.dict(os.environ, env_missing, clear=False):
            # Force empty
            os.environ["POSTGRES_HOST"] = ""
            os.environ["MONGO_URI"] = ""
            if "utils.engine" in sys.modules:
                del sys.modules["utils.engine"]
            try:
                import utils.engine as eng

                importlib.reload(eng)
                assert False, "should have raised"
            except OSError as exc:
                msg = str(exc)
                assert "Missing required environment variables" in msg
                assert "POSTGRES_HOST" in msg
                assert "MONGO_URI" in msg
    finally:
        if "utils.engine" in sys.modules:
            del sys.modules["utils.engine"]
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["MONGO_URI"] = "mongodb://localhost:27017"
        import utils.engine as _eng

        importlib.reload(_eng)


def test_optional_schema_warning():
    """Missing bronze/silver/gold schemas emit warnings, not errors."""
    _reload_engine(
        {
            "POSTGRES_SCHEMA_BRONZE": "",
            "POSTGRES_SCHEMA_SILVER": "",
            "POSTGRES_SCHEMA_GOLD": "",
        }
    )
    # Reload already happened — capture future reload warning
    import sys

    if "utils.engine" in sys.modules:
        del sys.modules["utils.engine"]
    os.environ["POSTGRES_SCHEMA_BRONZE"] = ""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import utils.engine as eng2

        importlib.reload(eng2)
        assert any("bronze/silver/gold" in str(x.message) for x in w)
    # Restore
    if "utils.engine" in sys.modules:
        del sys.modules["utils.engine"]
    os.environ["POSTGRES_SCHEMA_BRONZE"] = "bronze"
    os.environ["POSTGRES_SCHEMA_SILVER"] = "silver"
    os.environ["POSTGRES_SCHEMA_GOLD"] = "gold"
    import utils.engine as _eng

    importlib.reload(_eng)
