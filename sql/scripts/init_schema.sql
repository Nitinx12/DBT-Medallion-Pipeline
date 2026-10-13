-- ============================================================================
-- Script:       init_schema.sql
-- Purpose:      Bootstraps a fresh Postgres instance for the pipeline:
--               creates the walmart_db database (if missing) and the three
--               medallion schemas (bronze/silver/gold).
--
-- Run with psql (meta-commands below need psql, not a generic driver):
--   psql -U postgres -f sql/scripts/init_schema.sql
--
-- Why \gexec instead of CREATE DATABASE IF NOT EXISTS:
--   Postgres has no such clause for databases, so the SELECT discovers
--   absence and \gexec executes the generated CREATE only when a row
--   comes back. Plain SELECT without \gexec would only print the string.
-- ============================================================================

-- Create the database if it does not already exist.
SELECT 'CREATE DATABASE walmart_db'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'walmart_db'
) \gexec

-- Connect to the database: schemas must live inside walmart_db, not the
-- maintenance database the session started in.
\c walmart_db

-- Medallion schemas: bronze holds raw extracts, silver cleaned data,
-- gold the star schema. IF NOT EXISTS keeps this safe to re-run.
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Schema descriptions for data catalog tooling.
COMMENT ON SCHEMA bronze IS 'Raw landing layer. Minimal transformation.';
COMMENT ON SCHEMA silver IS 'Cleansed and standardized intermediate layer.';
COMMENT ON SCHEMA gold IS 'Production warehouse: dimensions and facts.';
