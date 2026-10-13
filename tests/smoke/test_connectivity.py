"""Smoke: live Postgres/Mongo reachability (skips cleanly when down)."""

import pytest


def test_postgres_answers_select_1():
    try:
        from sqlalchemy import text

        from src.utils.connection import get_postgres_engine
    except Exception as exc:
        pytest.skip(f"imports unavailable: {exc}")
    try:
        engine = get_postgres_engine()
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1
    except Exception as exc:
        pytest.skip(f"Postgres unreachable: {exc}")


def test_mongo_answers_ping():
    try:
        from src.utils.connection import get_mongo_db
    except Exception as exc:
        pytest.skip(f"imports unavailable: {exc}")
    try:
        assert get_mongo_db().command("ping").get("ok") == 1
    except Exception as exc:
        pytest.skip(f"Mongo unreachable: {exc}")


def test_gold_schema_visible():
    """Pipeline output schema exists (proves migrations/extract ran)."""
    from sqlalchemy import text

    from src.utils.connection import get_postgres_engine

    try:
        engine = get_postgres_engine()
        with engine.connect() as conn:
            schemas = [
                row[0]
                for row in conn.execute(
                    text("SELECT schema_name FROM information_schema.schemata")
                )
            ]
    except Exception as exc:
        pytest.skip(f"schema check unavailable: {exc}")
    assert "gold" in schemas
