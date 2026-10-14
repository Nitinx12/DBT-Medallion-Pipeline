@echo off
REM ==============================================================================
REM Walmart Data Pipeline — Windows batch runner (8 stages, strict order).
REM CMD-native mirror of pipeline\run_pipeline.ps1 and `make data-pipeline`.
REM Stops immediately when any stage fails (ERRORLEVEL 1).
REM
REM Usage:
REM   run_pipeline.bat        run the full pipeline (double-click works too)
REM ==============================================================================
setlocal EnableDelayedExpansion

REM This script lives at the repo root, so run from its own folder.
set "PROJECT_ROOT=%~dp0"
pushd "%PROJECT_ROOT%" || exit /b 1

set "PYTHONPATH=%CD%"
set "PYTHONIOENCODING=utf-8"

REM Load .env into the process (skip blanks and # comments). Values are taken
REM verbatim after the first `=`; surrounding double quotes are stripped.
if exist ".env" (
    for /f "usebackq tokens=1* delims==" %%A in (".env") do (
        set "k=%%A"
        set "v=%%B"
        if defined k (
            set "kc=!k: =!"
            if not "!kc!"=="" if not "!kc:~0,1!"=="#" (
                set "v=!v:"=!"
                set "!kc!=!v!"
            )
        )
    )
) else (
    echo WARNING: .env was not found; using environment variables already set in this shell.
)

where uv >nul 2>nul
if errorlevel 1 (
    echo [FAIL] uv is not available on PATH. Install uv, then run 'uv sync'.
    popd
    exit /b 1
)

set "STAGE=Preflight"
echo ------------------------------------------------------------
echo  STEP 0 / 7  -  PREFLIGHT ^(dependency check^)
echo ------------------------------------------------------------
call uv run python -c "import pyspark; assert pyspark.__version__.startswith('3.5'), f'Incompatible PySpark version: {pyspark.__version__}. Requires 3.5.x'"
if errorlevel 1 goto :fail

set "STAGE=Extract"
echo ------------------------------------------------------------
echo  STEP 1 / 7  -  EXTRACT ^(MongoDB to Bronze^)
echo ------------------------------------------------------------
call uv run python src/jobs/extract.py
if errorlevel 1 goto :fail

set "STAGE=Bronze Tests"
echo ------------------------------------------------------------
echo  STEP 2 / 7  -  BRONZE SQL TESTS
echo ------------------------------------------------------------
call uv run python src/jobs/sql_test.py tests/data-quality/bronze
if errorlevel 1 goto :fail

set "STAGE=Silver dbt"
echo ------------------------------------------------------------
echo  STEP 3 / 7  -  DBT SILVER ^(build and test^)
echo ------------------------------------------------------------
call uv run dbt run --project-dir dbt --profiles-dir dbt --select silver
if errorlevel 1 goto :fail
call uv run dbt test --project-dir dbt --profiles-dir dbt --select silver
if errorlevel 1 goto :fail

set "STAGE=Silver Tests"
echo ------------------------------------------------------------
echo  STEP 4 / 7  -  SILVER SQL TESTS
echo ------------------------------------------------------------
call uv run python src/jobs/sql_test.py tests/data-quality/silver
if errorlevel 1 goto :fail

set "STAGE=Gold dbt"
echo ------------------------------------------------------------
echo  STEP 5 / 7  -  DBT GOLD ^(build and test^)
echo ------------------------------------------------------------
call uv run dbt run --project-dir dbt --profiles-dir dbt --select gold
if errorlevel 1 goto :fail
call uv run dbt test --project-dir dbt --profiles-dir dbt --select gold
if errorlevel 1 goto :fail

set "STAGE=Gold Tests"
echo ------------------------------------------------------------
echo  STEP 6 / 7  -  GOLD SQL TESTS
echo ------------------------------------------------------------
call uv run python src/jobs/sql_test.py tests/data-quality/gold
if errorlevel 1 goto :fail

set "STAGE=Great Expectations"
echo ------------------------------------------------------------
echo  STEP 7 / 7  -  GREAT EXPECTATIONS TESTS ^(Bronze, Silver, Gold^)
echo ------------------------------------------------------------
call uv run python -m gx.run --layer all
if errorlevel 1 goto :fail

echo.
echo PIPELINE COMPLETE - all 8 stages passed.
popd
exit /b 0

:fail
echo [FAIL] %STAGE% failed. Stopping pipeline. See logs/ for detail.
popd
exit /b 1
