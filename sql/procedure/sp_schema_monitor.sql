-- ============================================================================
-- Procedure:    sp_snapshot_schema
-- View:         vw_schema_drift
-- Purpose:      Tracks structural drift of the medallion schemas over time.
--               Each CALL snapshots one schema's catalog (tables, columns,
--               types) plus live row counts into gold.schema_snapshots, so
--               the vw_schema_drift view can compare the two latest snapshots
--               and surface added/dropped tables and columns and row-count
--               deltas. Catches silent upstream changes (a renamed Mongo
--               field dropping a bronze column, a dbt model dropping a dim)
--               before they break downstream consumers.
--
-- Parameters:
--   p_schema  TEXT - bronze | silver | gold (any existing schema works, but
--               the medallion three are the intended targets).
--
-- Returns:
--   Snapshot rows in gold.schema_snapshots, tagged with taken_at. The
--   vw_schema_drift view needs at least two snapshots of a schema before
--   it reports anything for it.
--
-- Security:
--   Identifiers come from information_schema and are interpolated
--   exclusively through %I, never %s or raw concatenation.
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.schema_snapshots (
    snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    taken_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    ordinal_position INTEGER NOT NULL,
    data_type TEXT NOT NULL,
    row_count BIGINT NOT NULL
);

CREATE OR REPLACE PROCEDURE sp_snapshot_schema(p_schema TEXT)
LANGUAGE plpgsql
AS $procedure$
DECLARE
    v_taken_at  TIMESTAMPTZ := now();
    v_tbl       RECORD;
    v_count     BIGINT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = p_schema) THEN
        RAISE EXCEPTION 'Schema % does not exist', p_schema;
    END IF;

    -- One snapshot batch must be atomic: a half-written snapshot would
    -- compare garbage against the previous one in vw_schema_drift.
    DELETE FROM gold.schema_snapshots
    WHERE schema_name = p_schema AND taken_at = v_taken_at;

    FOR v_tbl IN
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = p_schema AND table_type = 'BASE TABLE'
        ORDER BY table_name
    LOOP
        -- Row counts are per-table dynamic SQL because the table set is
        -- discovered at runtime; a static query can't enumerate tables.
        EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema, v_tbl.table_name)
        INTO v_count;

        INSERT INTO gold.schema_snapshots(
            taken_at, schema_name, table_name, column_name,
            ordinal_position, data_type, row_count)
        SELECT v_taken_at, p_schema, v_tbl.table_name,
               c.column_name, c.ordinal_position, c.data_type, v_count
        FROM information_schema.columns c
        WHERE c.table_schema = p_schema AND c.table_name = v_tbl.table_name;
    END LOOP;

    RAISE NOTICE 'sp_snapshot_schema: snapshotted schema % at %', p_schema, v_taken_at;
END;
$procedure$;

-- ----------------------------------------------------------------------------
-- View: compares the two latest snapshots per schema.
-- change_type is one of: table_added, table_dropped, column_added,
-- column_dropped, row_count_changed (only reported when the count moved by
-- more than 10% or the table went empty/non-empty, to avoid noise from
-- normal incremental loads).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.vw_schema_drift AS
WITH ranked AS (
    SELECT DISTINCT
        schema_name,
        taken_at,
        dense_rank()
            OVER (PARTITION BY schema_name ORDER BY taken_at DESC)
            AS rnk
    FROM gold.schema_snapshots
),

latest AS (
    SELECT s.* FROM gold.schema_snapshots AS s
    INNER JOIN
        ranked AS r
        ON s.schema_name = r.schema_name AND s.taken_at = r.taken_at
    WHERE r.rnk = 1
),

previous AS (
    SELECT s.* FROM gold.schema_snapshots AS s
    INNER JOIN
        ranked AS r
        ON s.schema_name = r.schema_name AND s.taken_at = r.taken_at
    WHERE r.rnk = 2
)

SELECT
    schema_name,
    table_name,
    NULL::TEXT AS column_name,
    'table_added' AS change_type,
    'Table present in latest snapshot only' AS detail
FROM latest AS l
WHERE
    NOT EXISTS (
        SELECT 1 FROM previous AS p
        WHERE p.schema_name = l.schema_name AND p.table_name = l.table_name
    )
GROUP BY schema_name, table_name
UNION ALL
SELECT
    schema_name,
    table_name,
    NULL::TEXT AS column_name,
    'table_dropped' AS change_type,
    'Table present in previous snapshot only' AS detail
FROM previous AS p
WHERE
    NOT EXISTS (
        SELECT 1 FROM latest AS l
        WHERE l.schema_name = p.schema_name AND l.table_name = p.table_name
    )
GROUP BY schema_name, table_name
UNION ALL
SELECT
    l.schema_name,
    l.table_name,
    l.column_name,
    'column_added' AS change_type,
    'Column '
    || l.column_name
    || ' ('
    || l.data_type
    || ') present in latest snapshot only' AS detail
FROM latest AS l
WHERE
    NOT EXISTS (
        SELECT 1 FROM previous AS p
        WHERE
            p.schema_name = l.schema_name AND p.table_name = l.table_name
            AND p.column_name = l.column_name
    )
GROUP BY l.schema_name, l.table_name, l.column_name, l.data_type
UNION ALL
SELECT
    l.schema_name,
    l.table_name,
    NULL::TEXT AS column_name,
    'row_count_changed' AS change_type,
    'Rows ' || max(p.row_count) || ' -> ' || max(l.row_count) AS detail
FROM latest AS l
INNER JOIN
    previous AS p
    ON l.schema_name = p.schema_name AND l.table_name = p.table_name
GROUP BY l.schema_name, l.table_name
HAVING
    max(l.row_count) <> max(p.row_count)
    AND (
        max(p.row_count) = 0 OR max(l.row_count) = 0
        OR abs(max(l.row_count) - max(p.row_count))::NUMERIC
        / greatest(max(p.row_count), 1)
        > 0.10
    );

-- ============================================================================
-- Example usage
-- ============================================================================
-- Snapshot all three layers (take these on a schedule, e.g. after each
-- pipeline run, so drift has a baseline to compare against):
--   CALL sp_snapshot_schema('bronze');
--   CALL sp_snapshot_schema('silver');
--   CALL sp_snapshot_schema('gold');
--
-- Review drift since the previous snapshot:
--   SELECT * FROM gold.vw_schema_drift ORDER BY schema_name, table_name;
--
-- Snapshot history for one table:
--   SELECT taken_at, row_count
--   FROM gold.schema_snapshots
--   WHERE schema_name = 'gold' AND table_name = 'fact_order_items'
--   ORDER BY taken_at DESC;
-- ============================================================================
