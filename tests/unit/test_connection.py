from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_caches():
    """Clear cached singletons before/after each test."""
    import utils.connection as conn

    conn._mongo_client = None
    conn._postgres_engine = None
    conn._databricks_connection = None
    yield
    conn._mongo_client = None
    conn._postgres_engine = None
    conn._databricks_connection = None


# ── Postgres ──────────────────────────────────────────────────────────


def test_get_postgres_engine_builds_url_with_ssl_params():
    """get_postgres_engine builds URL via URL.create and caches."""
    import utils.connection as conn
    import utils.engine as cfg

    fake_engine = MagicMock()
    fake_engine.connect.return_value.__enter__.return_value = MagicMock()

    with (
        patch(
            "utils.connection.create_engine", return_value=fake_engine
        ) as mock_create,
        patch("utils.connection.URL") as mock_url,
    ):
        mock_url.create.return_value = "postgresql+psycopg2://url"

        # Force ssl params present to test query building
        with (
            patch.object(cfg, "POSTGRES_SSLMODE", "require"),
            patch.object(cfg, "POSTGRES_CHANNEL_BINDING", "require"),
        ):
            engine = conn.get_postgres_engine()
            assert engine is fake_engine
            # cached second call does not re-create
            engine2 = conn.get_postgres_engine()
            assert engine2 is fake_engine
            mock_create.assert_called_once()
            # URL.create called with query containing sslmode/channel_binding
            _, kwargs = mock_url.create.call_args
            assert kwargs["query"]["sslmode"] == "require"

        # failure path — SQLAlchemyError resets cache and re-raises
        conn._postgres_engine = None
        mock_create.side_effect = __import__("sqlalchemy.exc").exc.SQLAlchemyError(
            "boom"
        )
        with pytest.raises(__import__("sqlalchemy.exc").exc.SQLAlchemyError):
            conn.get_postgres_engine()
        assert conn._postgres_engine is None


# ── Mongo ─────────────────────────────────────────────────────────────


def test_get_mongo_db_caches_and_pings():
    import utils.connection as conn
    import utils.engine as cfg

    fake_client = MagicMock()
    fake_client.admin.command.return_value = {"ok": 1}
    fake_db = MagicMock()
    fake_client.__getitem__.return_value = fake_db

    with patch("utils.connection.MongoClient", return_value=fake_client) as mock_client:
        db = conn.get_mongo_db()
        assert db is fake_db
        mock_client.assert_called_once_with(cfg.MONGO_URI)
        fake_client.admin.command.assert_called_once_with("ping")
        # cached
        db2 = conn.get_mongo_db()
        assert db2 is fake_db
        mock_client.assert_called_once()  # still once


def test_get_mongo_db_failure_resets_cache():
    from pymongo.errors import PyMongoError

    import utils.connection as conn

    with patch("utils.connection.MongoClient", side_effect=PyMongoError("auth fail")):
        with pytest.raises(PyMongoError):
            conn.get_mongo_db()
        assert conn._mongo_client is None


# ── Databricks ────────────────────────────────────────────────────────


def test_get_databricks_connection_missing_env_raises():
    import utils.connection as conn
    import utils.engine as cfg

    with (
        patch.object(cfg, "DATABRICKS_HOST", None),
        patch.object(cfg, "DATABRICKS_HTTP_PATH", None),
        patch.object(cfg, "DATABRICKS_TOKEN", None),
        pytest.raises(
            OSError, match="Missing required environment variables for Databricks"
        ),
    ):
        conn.get_databricks_connection()


def test_get_databricks_connection_success_injects_catalog_schema():
    import utils.connection as conn
    import utils.engine as cfg

    fake_conn = MagicMock()
    fake_cursor_ctx = MagicMock()
    fake_cursor = fake_cursor_ctx.__enter__.return_value
    fake_conn.cursor.return_value = fake_cursor_ctx

    with (
        patch(
            "utils.connection.databricks_sql.connect", return_value=fake_conn
        ) as mock_connect,
        patch.object(cfg, "DATABRICKS_HOST", "host.cloud.databricks.com"),
        patch.object(cfg, "DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc"),
        patch.object(cfg, "DATABRICKS_TOKEN", "dapi_token"),
        patch.object(cfg, "DATABRICKS_CATALOG", "walmart"),
        patch.object(cfg, "DATABRICKS_SCHEMA", "gold"),
    ):
        dbx = conn.get_databricks_connection()
        assert dbx is fake_conn
        mock_connect.assert_called_once()
        _, kwargs = mock_connect.call_args
        assert kwargs["catalog"] == "walmart"
        assert kwargs["schema"] == "gold"
        fake_cursor.execute.assert_called_once_with("SELECT 1")

        # cached
        dbx2 = conn.get_databricks_connection()
        assert dbx2 is fake_conn
        mock_connect.assert_called_once()


def test_get_databricks_connection_omits_none_catalog():
    """When catalog/schema are None, they are omitted from connect kwargs."""
    import utils.connection as conn
    import utils.engine as cfg

    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = MagicMock()
    with (
        patch(
            "utils.connection.databricks_sql.connect", return_value=fake_conn
        ) as mock_connect,
        patch.object(cfg, "DATABRICKS_HOST", "h"),
        patch.object(cfg, "DATABRICKS_HTTP_PATH", "/p"),
        patch.object(cfg, "DATABRICKS_TOKEN", "t"),
        patch.object(cfg, "DATABRICKS_CATALOG", None),
        patch.object(cfg, "DATABRICKS_SCHEMA", None),
    ):
        conn.get_databricks_connection()
        _, kwargs = mock_connect.call_args
        assert "catalog" not in kwargs
        assert "schema" not in kwargs
