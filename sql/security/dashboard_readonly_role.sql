-- ============================================================================
-- Script:       dashboard_readonly_role.sql
-- Purpose:      Least privilege role for the dashboard database user.
--               The public app must never connect as a schema owner.
--
-- Run once per warehouse (local AND Neon) as a superuser, replacing the
-- placeholder below with a strong generated secret first. The secret
-- lives in Streamlit secrets / env vars afterwards, never in this file.
--
--   psql -U postgres -d walmart_db -f sql/security/dashboard_readonly_role.sql
-- ============================================================================

DO
$$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'dashboard_ro'
    ) THEN
        CREATE ROLE dashboard_ro WITH LOGIN PASSWORD 'REPLACE_WITH_STRONG_SECRET';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA gold TO dashboard_ro;

GRANT SELECT ON ALL TABLES IN SCHEMA gold TO dashboard_ro;

-- Future gold tables stay readable without re-running this file. Note:
-- this binds to the user who runs it, so run it as the schema owner.
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO dashboard_ro;
