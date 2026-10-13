-- ============================================================================
-- Procedure:    sp_run_dq_tests
-- Purpose:      Runs the repository's data-quality checks natively inside
--               Postgres and records every check in gold.dq_test_runs, so a
--               full layer gets a complete PASS/FAIL picture in one CALL.
--               This complements src/jobs/sql_test.py (which runs the
--               tests/data-quality/*.sql files and stops a pipeline stage on
--               the first failing file): the procedure never aborts early -
--               each check is isolated, so one bad table can't hide the
--               results for the rest of the layer.
--
-- Checks mirror tests/data-quality/:
--   bronze : every base table non-empty; metadata columns (_id,
--            created_timestamp, updated_timestamp, is_active) present.
--   silver : first-column duplicate check + first-column null check per
--            table (same "first column is the business key" convention as
--            01_lp_check_duplicates.sql).
--   gold   : every table non-empty; silver-vs-gold row-count parity for the
--            1:1 table mapping (same mapping as 07_row_count_validation.sql).
--
-- Parameters:
--   p_passed  OUT INTEGER - number of checks that passed.
--   p_failed  OUT INTEGER - number of checks that failed.
--   p_layer   TEXT - bronze | silver | gold | all (default: 'all').
--             Listed last because Postgres forbids OUT parameters after
--             a parameter with a default value.
--
-- Returns:
--   Results are written to gold.dq_test_runs (one row per check) and
--   summarized with RAISE NOTICE. OUT params carry the totals so callers
--   (psql, Airflow, dbt) can gate on them without parsing notices.
--
-- Security:
--   Table/column identifiers come from information_schema or from a fixed
--   in-body mapping and are interpolated exclusively through %I, never %s
--   or raw concatenation.
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.dq_test_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    layer TEXT NOT NULL,
    check_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL')),
    detail TEXT NOT NULL DEFAULT ''
);

CREATE OR REPLACE PROCEDURE sp_run_dq_tests(
    OUT p_passed INTEGER,
    OUT p_failed INTEGER,
    IN p_layer TEXT DEFAULT 'all'
)
LANGUAGE plpgsql
AS $procedure$
DECLARE
    v_run_at        TIMESTAMPTZ := now();
    v_tbl           RECORD;
    v_col           TEXT;
    v_count         BIGINT;
    v_silver_count  BIGINT;
    v_gold_count    BIGINT;
    v_map           RECORD;
BEGIN
    IF p_layer NOT IN ('bronze', 'silver', 'gold', 'all') THEN
        RAISE EXCEPTION 'Invalid p_layer: %. Allowed: bronze, silver, gold, all', p_layer;
    END IF;

    p_passed := 0;
    p_failed := 0;

    -- ------------------------------------------------------------------
    -- Bronze: non-empty tables + metadata columns
    -- ------------------------------------------------------------------
    IF p_layer IN ('bronze', 'all') THEN
        -- etl_logs / etl_watermarks are pipeline metadata, not source data,
        -- so they are excluded from validation like everywhere else.
        FOR v_tbl IN
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'bronze' AND table_type = 'BASE TABLE'
              AND table_name NOT IN ('etl_logs', 'etl_watermarks')
            ORDER BY table_name
        LOOP
            BEGIN
                EXECUTE format('SELECT COUNT(*) FROM bronze.%I', v_tbl.table_name)
                INTO v_count;
                IF v_count = 0 THEN
                    RAISE EXCEPTION 'Table is empty';
                END IF;
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'bronze', 'non_empty', v_tbl.table_name, 'PASS', v_count || ' rows');
                p_passed := p_passed + 1;
            EXCEPTION WHEN OTHERS THEN
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'bronze', 'non_empty', v_tbl.table_name, 'FAIL', SQLERRM);
                p_failed := p_failed + 1;
            END;

            -- Metadata columns are the lineage contract with Mongo: every
            -- bronze table must carry them, otherwise _id/watermark logic
            -- downstream has nothing to key off.
            BEGIN
                SELECT string_agg(m.col, ', ' ORDER BY m.col) INTO v_col
                FROM (VALUES ('_id'), ('created_timestamp'), ('updated_timestamp'), ('is_active')) AS m(col)
                WHERE NOT EXISTS (
                    SELECT 1 FROM information_schema.columns c
                    WHERE c.table_schema = 'bronze' AND c.table_name = v_tbl.table_name
                      AND c.column_name = m.col
                );
                IF v_col IS NOT NULL THEN
                    RAISE EXCEPTION 'Missing metadata column(s): %', v_col;
                END IF;
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'bronze', 'metadata_columns', v_tbl.table_name, 'PASS', 'all present');
                p_passed := p_passed + 1;
            EXCEPTION WHEN OTHERS THEN
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'bronze', 'metadata_columns', v_tbl.table_name, 'FAIL', SQLERRM);
                p_failed := p_failed + 1;
            END;
        END LOOP;
    END IF;

    -- ------------------------------------------------------------------
    -- Silver: first-column duplicates + nulls
    -- ------------------------------------------------------------------
    IF p_layer IN ('silver', 'all') THEN
        FOR v_tbl IN
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'silver' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        LOOP
            SELECT column_name INTO v_col
            FROM information_schema.columns
            WHERE table_schema = 'silver' AND table_name = v_tbl.table_name
            ORDER BY ordinal_position LIMIT 1;

            BEGIN
                EXECUTE format(
                    'SELECT COUNT(*) FROM (SELECT %I FROM silver.%I GROUP BY %I HAVING COUNT(*) > 1) x',
                    v_col, v_tbl.table_name, v_col)
                INTO v_count;
                IF v_count > 0 THEN
                    RAISE EXCEPTION '% duplicate value(s) on %', v_count, v_col;
                END IF;
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'silver', 'no_duplicates', v_tbl.table_name, 'PASS', 'column ' || v_col);
                p_passed := p_passed + 1;
            EXCEPTION WHEN OTHERS THEN
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'silver', 'no_duplicates', v_tbl.table_name, 'FAIL', SQLERRM);
                p_failed := p_failed + 1;
            END;

            BEGIN
                EXECUTE format('SELECT COUNT(*) FROM silver.%I WHERE %I IS NULL',
                    v_tbl.table_name, v_col)
                INTO v_count;
                IF v_count > 0 THEN
                    RAISE EXCEPTION '% NULL value(s) on %', v_count, v_col;
                END IF;
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'silver', 'no_nulls', v_tbl.table_name, 'PASS', 'column ' || v_col);
                p_passed := p_passed + 1;
            EXCEPTION WHEN OTHERS THEN
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'silver', 'no_nulls', v_tbl.table_name, 'FAIL', SQLERRM);
                p_failed := p_failed + 1;
            END;
        END LOOP;
    END IF;

    -- ------------------------------------------------------------------
    -- Gold: non-empty tables + silver-vs-gold row-count parity
    -- ------------------------------------------------------------------
    IF p_layer IN ('gold', 'all') THEN
        -- dq_test_runs / schema_snapshots are this procedure's own
        -- monitoring tables: legitimately empty before their first run,
        -- so they are excluded like the bronze etl_* tables.
        FOR v_tbl IN
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'gold' AND table_type = 'BASE TABLE'
              AND table_name NOT IN ('dq_test_runs', 'schema_snapshots')
            ORDER BY table_name
        LOOP
            BEGIN
                EXECUTE format('SELECT COUNT(*) FROM gold.%I', v_tbl.table_name)
                INTO v_count;
                IF v_count = 0 THEN
                    RAISE EXCEPTION 'Table is empty';
                END IF;
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'gold', 'non_empty', v_tbl.table_name, 'PASS', v_count || ' rows');
                p_passed := p_passed + 1;
            EXCEPTION WHEN OTHERS THEN
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'gold', 'non_empty', v_tbl.table_name, 'FAIL', SQLERRM);
                p_failed := p_failed + 1;
            END;
        END LOOP;

        -- Parity only makes sense for 1:1 tables (fact_order_items is
        -- line-grain, so silver.order_items vs gold.fact_order_items must
        -- match exactly; aggregates would be excluded here by design).
        FOR v_map IN
            SELECT * FROM (VALUES
                ('brands', 'dim_brands'), ('categories', 'dim_categories'),
                ('customers', 'dim_customers'), ('orders', 'dim_orders'),
                ('payment_methods', 'dim_payment_methods'),
                ('products', 'dim_products'), ('stores', 'dim_stores'),
                ('order_items', 'fact_order_items')
            ) AS mapping(silver_table, gold_table)
        LOOP
            BEGIN
                EXECUTE format('SELECT COUNT(*) FROM silver.%I', v_map.silver_table)
                INTO v_silver_count;
                EXECUTE format('SELECT COUNT(*) FROM gold.%I', v_map.gold_table)
                INTO v_gold_count;
                IF v_silver_count <> v_gold_count THEN
                    RAISE EXCEPTION 'silver.% has % rows, gold.% has % rows',
                        v_map.silver_table, v_silver_count, v_map.gold_table, v_gold_count;
                END IF;
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'gold', 'row_parity', v_map.gold_table, 'PASS',
                        v_silver_count || ' = ' || v_gold_count);
                p_passed := p_passed + 1;
            EXCEPTION WHEN OTHERS THEN
                INSERT INTO gold.dq_test_runs(run_at, layer, check_name, table_name, status, detail)
                VALUES (v_run_at, 'gold', 'row_parity', v_map.gold_table, 'FAIL', SQLERRM);
                p_failed := p_failed + 1;
            END;
        END LOOP;
    END IF;

    RAISE NOTICE 'sp_run_dq_tests [%]: % passed, % failed (see gold.dq_test_runs)',
        p_layer, p_passed, p_failed;
END;
$procedure$;

-- ============================================================================
-- Example usage
-- ============================================================================
-- Full run across all layers (pass/fail totals come back as OUT params;
-- NULL placeholders need explicit casts so overload resolution succeeds):
--   CALL sp_run_dq_tests(NULL::INTEGER, NULL::INTEGER, 'all');
--
-- Single layer:
--   CALL sp_run_dq_tests(NULL::INTEGER, NULL::INTEGER, 'silver');
--
-- Review the latest run:
--   SELECT layer, check_name, table_name, status, detail
--   FROM gold.dq_test_runs
--   WHERE run_at = (SELECT MAX(run_at) FROM gold.dq_test_runs)
--   ORDER BY layer, table_name, check_name;
--
-- Failures only, across all runs:
--   SELECT run_at, layer, check_name, table_name, detail
--   FROM gold.dq_test_runs
--   WHERE status = 'FAIL'
--   ORDER BY run_at DESC;
-- ============================================================================
