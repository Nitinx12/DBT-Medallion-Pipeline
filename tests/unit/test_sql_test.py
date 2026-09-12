from unittest.mock import MagicMock, patch

from sqlalchemy.exc import ResourceClosedError


def _make_engine_mock(fetch_rows=None, raise_on_execute=None):
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = False
    if raise_on_execute:
        conn.execute.side_effect = raise_on_execute
    else:
        result = MagicMock()
        if isinstance(raise_on_execute, type) and issubclass(
            raise_on_execute, Exception
        ):
            pass
        else:
            result.fetchall.return_value = fetch_rows if fetch_rows is not None else []
            conn.execute.return_value = result
    return engine, conn


def test_run_tests_select_pass_and_fail(tmp_path):
    """SELECT returning rows = FAIL, empty = PASS."""
    import scripts.sql_test as st

    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    # two sql files: one will PASS (empty), one FAIL (rows)
    (test_dir / "01_pass.sql").write_text("SELECT * FROM silver.orders WHERE 1=0")
    (test_dir / "02_fail.sql").write_text(
        "SELECT * FROM silver.orders WHERE amount < 0"
    )

    # Mock engine: first execute returns [], second returns [rows]
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = False

    pass_result = MagicMock()
    pass_result.fetchall.return_value = []
    fail_result = MagicMock()
    fail_result.fetchall.return_value = [(1, -10), (2, -5)]

    conn.execute.side_effect = [pass_result, fail_result]

    log = MagicMock()
    with patch("scripts.sql_test.get_postgres_engine", return_value=engine):
        passed = st.run_tests(test_dir, log)

    assert passed is False  # one failure
    # PASS logs info, FAIL logs error
    assert any("01_pass.sql: PASS" in str(c) for c in log.info.call_args_list)
    assert any("02_fail.sql: FAIL" in str(c) for c in log.error.call_args_list)


def test_run_tests_do_block_resource_closed_is_pass(tmp_path):
    """DO $$ blocks raise ResourceClosedError on fetchall -> treated as PASS."""
    import scripts.sql_test as st

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "01_do.sql").write_text("DO $$ BEGIN RAISE NOTICE 'ok'; END $$;")

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    result = MagicMock()
    result.fetchall.side_effect = ResourceClosedError("no result set")
    conn.execute.return_value = result

    log = MagicMock()
    with patch("scripts.sql_test.get_postgres_engine", return_value=engine):
        passed = st.run_tests(test_dir, log)

    assert passed is True
    assert any("PASS" in str(c) for c in log.info.call_args_list)


def test_run_tests_exception_rolls_back_and_fails(tmp_path):
    """SQLAlchemyError suffix via RAISE EXCEPTION marks FAIL and rolls back."""
    from sqlalchemy.exc import SQLAlchemyError

    import scripts.sql_test as st

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "01_bad.sql").write_text(
        "DO $$ BEGIN RAISE EXCEPTION 'violated'; END $$;"
    )

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    conn.execute.side_effect = SQLAlchemyError("violated")

    log = MagicMock()
    with patch("scripts.sql_test.get_postgres_engine", return_value=engine):
        passed = st.run_tests(test_dir, log)

    assert passed is False
    conn.rollback.assert_called_once()
    assert any("FAIL" in str(c) for c in log.error.call_args_list)


def test_run_tests_empty_dir_warns(tmp_path):
    import scripts.sql_test as st

    empty = tmp_path / "empty"
    empty.mkdir()
    log = MagicMock()
    engine, _ = _make_engine_mock()
    with patch("scripts.sql_test.get_postgres_engine", return_value=engine):
        passed = st.run_tests(empty, log)
    assert passed is True
    log.warning.assert_called_once()
