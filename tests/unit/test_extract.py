from unittest.mock import MagicMock, patch

import pytest

# extract.py imports pyspark at top level — mock it if not installed
# In this repo pyspark IS installed, but mocking Spark internals keeps tests offline.
pytest.importorskip("pyspark", reason="pyspark required for extract tests")

import scripts.extract as ex

# ── detect_incremental_column ─────────────────────────────────────────


def test_detect_incremental_column_priority_order():
    """Candidates are checked in priority: updated_timestamp > updated_at > created_*."""
    # has updated_timestamp — wins even if others present
    assert (
        ex.detect_incremental_column(
            ["_id", "created_at", "updated_at", "updated_timestamp"], override=None
        )
        == "updated_timestamp"
    )

    # fallback to updated_at
    assert (
        ex.detect_incremental_column(["_id", "updated_at", "created_at"])
        == "updated_at"
    )

    # override wins when present, None when not present
    assert (
        ex.detect_incremental_column(["_id", "updated_at"], override="created_at")
        is None
    )
    assert (
        ex.detect_incremental_column(["_id", "created_at"], override="created_at")
        == "created_at"
    )

    # no candidate
    assert ex.detect_incremental_column(["_id", "name"], override=None) is None


# ── short_error ───────────────────────────────────────────────────────


def test_short_error_collapses_stack_frames():
    exc = Exception(
        'boom\nat com.foo.Bar.method(Bar.java:10)\nFile "foo.py", line 1\nmore'
    )
    msg = ex.short_error(exc)
    assert msg.startswith("Exception:")
    # stops before stack frames, collapsed
    assert "at com.foo.Bar" not in msg
    assert "--" in msg or "boom" in msg


def test_short_error_truncates():
    long_msg = "x" * 500
    msg = ex.short_error(Exception(long_msg), max_len=100)
    assert len(msg) <= len("Exception: ") + 100
    assert msg.endswith("…")


# ── discover_collections ──────────────────────────────────────────────


def test_discover_collections_filters_system_prefix():
    fake_db = MagicMock()
    fake_db.list_collection_names.return_value = [
        "orders",
        "system.indexes",
        "system.profile",
        "customers",
        "products",
    ]
    cols = ex.discover_collections(fake_db)
    assert cols == ["customers", "orders", "products"]  # sorted, system.* removed


# ── check_connector_compatibility ─────────────────────────────────────


def test_check_connector_compatibility_fails_on_spark4():
    with patch("scripts.extract.pyspark.__version__", "4.0.0"):
        with pytest.raises(SystemExit) as exc:
            ex.check_connector_compatibility()
        assert exc.value.code == 2


def test_check_connector_compatibility_passes_on_spark3():
    with patch("scripts.extract.pyspark.__version__", "3.5.5"):
        # should not raise
        ex.check_connector_compatibility()


# ── postgres_jdbc helpers ─────────────────────────────────────────────


def test_postgres_jdbc_url_and_properties():
    import utils.engine as cfg

    url = ex.postgres_jdbc_url()
    assert cfg.POSTGRES_HOST in url
    assert str(cfg.POSTGRES_PORT) in url
    props = ex.postgres_jdbc_properties()
    assert props["user"] == cfg.POSTGRES_USERNAME
    assert props["driver"] == "org.postgresql.Driver"


# ── table helpers (mocked engine) ─────────────────────────────────────


def test_table_exists_true_false():
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.scalar.return_value = True
    assert ex.table_exists(engine, "orders") is True

    conn.execute.return_value.scalar.return_value = False
    assert ex.table_exists(engine, "missing") is False


def test_get_row_count_zero_when_missing():
    engine = MagicMock()
    with patch("scripts.extract.table_exists", return_value=False):
        assert ex.get_row_count(engine, "missing") == 0

    with patch("scripts.extract.table_exists", return_value=True):
        conn = engine.connect.return_value.__enter__.return_value
        conn.execute.return_value.scalar.return_value = 42
        assert ex.get_row_count(engine, "orders") == 42


def test_has_unique_index_checks_pg_index():
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.fetchone.return_value = (1,)
    assert ex.has_unique_index_on(engine, "orders", "_id") is True

    conn.execute.return_value.fetchone.return_value = None
    assert ex.has_unique_index_on(engine, "orders", "_id") is False


def test_validate_collection_pass_fail():
    with patch("scripts.extract.get_row_count", return_value=100):
        status, detail = ex.validate_collection(MagicMock(), "orders", 100)
        assert status == "PASS"
        assert "100" in detail

        status, detail = ex.validate_collection(MagicMock(), "orders", 99)
        assert status == "FAIL"
        assert "expected" in detail


# ── sanitize_for_postgres (DataFrame mock) ────────────────────────────


def test_sanitize_for_postgres_flattens_complex():
    from pyspark.sql.types import (
        ArrayType,
        IntegerType,
        MapType,
        StringType,
        StructField,
        StructType,
    )

    # Build minimal fake schema
    schema = StructType(
        [
            StructField("_id", StringType(), True),
            StructField("name", StringType(), True),
            StructField("tags", ArrayType(StringType()), True),
            StructField("meta", MapType(StringType(), StringType()), True),
            StructField("nested", StructType([StructField("x", IntegerType())]), True),
        ]
    )

    df = MagicMock()
    df.columns = ["_id", "name", "tags", "meta", "nested"]
    df.schema = schema

    # withColumn returns new mock each time — chain
    df.withColumn.side_effect = lambda name, col: MagicMock(
        columns=df.columns, schema=schema, withColumn=df.withColumn
    )

    # Patch pyspark functions used
    with patch("scripts.extract.F") as mock_F:
        mock_F.col.return_value.cast.return_value = MagicMock()
        mock_F.to_json.return_value = MagicMock()
        flattened: list = []
        ex.sanitize_for_postgres(df, flattened)
        # _id cast called
        mock_F.col.assert_any_call("_id")
        # complex fields flattened
        assert set(flattened) == {"tags", "meta", "nested"}
        # to_json called for each complex field
        assert mock_F.to_json.call_count == 3
