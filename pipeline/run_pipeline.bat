@echo off
REM =============================================================================
REM Walmart Medallion Pipeline — Windows Batch runner (CMD mirror of
REM pipeline/run_pipeline.ps1 and scripts/bash/run_pipeline.sh)
REM
REM Runs the fixed 8-stage pipeline in strict order, stopping immediately
REM when any command fails:
REM   0. Preflight            (pyspark 3.5.x version check)
REM   1. Extract              (MongoDB -> bronze  via scripts/python/extract.py)
REM   2. Bronze SQL tests     (tests/bronze)
REM   3. dbt Silver           (dbt run + test --select silver)
REM   4. Silver SQL tests     (tests/silver)
REM   5. dbt Gold             (dbt run + test --select gold)
REM   6. Gold SQL tests       (tests/gold)
REM   7. Great Expectations   (Bronze/Silver/Gold)
REM
REM Usage:
REM   pipeline\run_pipeline.bat              — run full pipeline
REM   pipeline\run_pipeline.bat --help       — show help
REM   pipeline\run_pipeline.bat --dry-run    — forward to extract --dry-run
REM   pipeline\run_pipeline.bat --full-refresh
REM   pipeline\run_pipeline.bat --tables orders,customers
REM
REM Requirements: uv on PATH, .env at project root, Python 3.11+
REM Logs: logs\pipeline_YYYY-MM-DD.log
REM Exit codes: 0 all passed, 1 stage failed
REM =============================================================================
setlocal EnableExtensions EnableDelayedExpansion

REM ---- Resolve project root (one level up from this file's dir) ---------------
set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash for clean join
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."
REM Normalize: pushd/popd to get absolute path without ..
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

set "DBT_DIR=%PROJECT_ROOT%\dbt"
set "LOG_DIR=%PROJECT_ROOT%\logs"

REM ---- Logging setup ----------------------------------------------------------
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "LOG_DATE=%%I"
if not defined LOG_DATE set "LOG_DATE=%date:~10,4%-%date:~4,2%-%date:~7,2%"
set "LOG_FILE=%LOG_DIR%\pipeline_%LOG_DATE%.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

REM ---- Colors (ANSI, works on Windows 10+; degrades gracefully) --------------
REM Use ESC character for ANSI
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RESET=%ESC%[0m"
set "BOLD=%ESC%[1m"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "CYAN=%ESC%[96m"
set "GRAY=%ESC%[90m"
set "DIM=%ESC%[2m"

REM ---- Env --------------------------------------------------------------------
set "PYTHONPATH=%PROJECT_ROOT%"
set "PYTHONIOENCODING=utf-8"
set "TOTAL_STAGES=7"

REM ---- Parse args -------------------------------------------------------------
set "EXTRACT_ARGS="
set "SHOW_HELP=0"

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--help" set "SHOW_HELP=1"
if /I "%~1"=="-h" set "SHOW_HELP=1"
if /I "%~1"=="--help" goto :args_done
if /I "%~1"=="-h" goto :args_done
REM Collect all args to forward to extract.py (extract handles unknown args)
set "EXTRACT_ARGS=%EXTRACT_ARGS% %~1"
shift
goto :parse_args
:args_done

if "%SHOW_HELP%"=="1" (
    echo %BOLD%Walmart Medallion Pipeline%RESET% — Windows Batch runner
    echo.
    echo Usage: pipeline\run_pipeline.bat [OPTIONS]
    echo.
    echo Runs the 8 stages in order, stopping on first failure.
    echo Same gate as pipeline\run_pipeline.ps1 and the Airflow DAG.
    echo.
    echo Options forwarded to extract stage:
    echo   --help, -h              Show this help
    echo   --dry-run               extract --dry-run [no writes]
    echo   --full-refresh          extract --full-refresh
    echo   --tables LIST           extract --tables LIST  [e.g. orders,customers]
    echo   --tables=LIST           same, equals form
    echo.
    echo Examples:
    echo   pipeline\run_pipeline.bat
    echo   pipeline\run_pipeline.bat --dry-run
    echo   pipeline\run_pipeline.bat --tables orders,customers --full-refresh
    echo.
    echo Other entry points:
    echo   powershell:  .\pipeline\run_pipeline.ps1
    echo   bash:        bash scripts/bash/run_pipeline.sh
    echo   docker:      docker compose -f docker\compose.yml up
    echo   python:      uv run python main.py
    exit /b 0
)

REM ---- Helpers ----------------------------------------------------------------

REM Log helper: call :log INFO "message"
goto :main

:log
set "LOG_LEVEL=%~1"
set "LOG_MSG=%~2"
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "LOG_TS=%%T"
if not defined LOG_TS set "LOG_TS=%date% %time%"
>>"%LOG_FILE%" echo %LOG_TS% ^| %LOG_LEVEL%    ^| pipeline ^| %LOG_MSG%
exit /b 0

:stage_header
echo.
echo %GRAY%------------------------------------------------------------%RESET%
echo %CYAN% STEP %~1 / %TOTAL_STAGES%  -  %~2%RESET%
echo %GRAY%------------------------------------------------------------%RESET%
call :log "INFO" "%~2"
exit /b 0

:stage_pass
echo %GREEN% [PASS] %~1%RESET%
call :log "INFO" "PASS - %~1"
REM track for summary
set "RESULT_%~2=PASS"
exit /b 0

:stage_fail
echo %RED% [FAIL] %~1%RESET%
call :log "ERROR" "FAIL - %~1"
set "RESULT_%~2=FAIL"
exit /b 1

:print_summary
echo.
echo %GRAY%------------------------------------------------------------%RESET%
echo %CYAN% PIPELINE SUMMARY%RESET%
echo %GRAY%------------------------------------------------------------%RESET%
for %%S in (Preflight Extract "Bronze Tests" "Silver dbt" "Silver Tests" "Gold dbt" "Gold Tests" "Great Expectations") do (
    set "KEY=%%~S"
    call set "STATUS=%%RESULT_!KEY!%%"
    if not defined STATUS set "STATUS=SKIP"
    if "!STATUS!"=="PASS" (
        echo %GREEN% !KEY!                         !STATUS!%RESET%
    ) else if "!STATUS!"=="FAIL" (
        echo %RED% !KEY!                         !STATUS!%RESET%
    ) else (
        echo %YELLOW% !KEY!                         !STATUS!%RESET%
    )
)
echo %GRAY%------------------------------------------------------------%RESET%
exit /b 0

REM ---- Main -------------------------------------------------------------------
:main
REM Clear screen if interactive (like ps1 -NoClear)
REM Only clear if not redirected
>nul 2>&1 powershell -NoProfile -Command "if (-not [Console]::IsOutputRedirected) { Clear-Host }"
pushd "%PROJECT_ROOT%"

echo %BOLD%Walmart Medallion Pipeline%RESET% %DIM%— CMD runner%RESET%
echo %DIM%Project root: %PROJECT_ROOT%%RESET%
echo %DIM%Log file: %LOG_FILE%%RESET%
call :log "INFO" "Pipeline started from %PROJECT_ROOT% (CMD runner)"

REM ---- Load .env (if present, like ps1 Import-DotEnv) ------------------------
if exist "%PROJECT_ROOT%\.env" (
    echo %GRAY%Loading .env...%RESET%
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%PROJECT_ROOT%\.env") do (
        set "ENV_KEY=%%A"
        set "ENV_VAL=%%B"
        REM Trim spaces from key
        for /f "tokens=*" %%K in ("!ENV_KEY!") do set "ENV_KEY=%%K"
        if defined ENV_KEY (
            REM Only set if not blank and key doesn't start with #
            REM Use setlocal trick to avoid overwriting already-set vars? ps1 overwrites; keep ps1 behavior
            set "!ENV_KEY!=!ENV_VAL!"
        )
    )
) else (
    echo %YELLOW% .env not found; using environment variables already set in this shell.%RESET%
    call :log "WARNING" ".env not found; using shell env"
)

REM ---- Prerequisite checks ----------------------------------------------------
echo %GRAY%Checking prerequisites...%RESET%

set "MISSING=0"
for %%P in (pyproject.toml "scripts\python\extract.py" "scripts\python\sql_test.py" "tests\bronze" "tests\silver" "tests\gold" "dbt\dbt_project.yml") do (
    if not exist "%PROJECT_ROOT%\%%~P" (
        echo %RED% Required path missing: %%~P%RESET%
        set "MISSING=1"
    )
)
if "%MISSING%"=="1" (
    echo %RED%Prerequisite check failed.%RESET%
    call :log "ERROR" "Prerequisite check failed"
    popd
    exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
    echo %RED% uv is not available on PATH. Install uv, then run 'uv sync'.%RESET%
    echo   See: https://docs.astral.sh/uv/getting-started/installation/
    call :log "ERROR" "uv not found on PATH"
    popd
    exit /b 1
)
echo %GREEN% Prerequisites OK%RESET%

REM =========================================================================
REM STAGE 0 — PREFLIGHT
REM =========================================================================
call :stage_header "0" "PREFLIGHT (dependency check)"
REM Mirror ps1 Invoke-Preflight: pyspark must be importable and 3.5.x
uv run python -c "import pyspark; print(pyspark.__version__)" >"%TEMP%\walmart_pyspark_ver.txt" 2>&1
set "PREFLIGHT_EC=%ERRORLEVEL%"
set "PYSPARK_VER="
if exist "%TEMP%\walmart_pyspark_ver.txt" (
    for /f "usebackq delims=" %%V in ("%TEMP%\walmart_pyspark_ver.txt") do set "PYSPARK_VER=%%V"
)
REM Trim
for /f "tokens=*" %%T in ("!PYSPARK_VER!") do set "PYSPARK_VER=%%T"

if not "%PREFLIGHT_EC%"=="0" (
    echo %RED% PySpark could not be imported. Run 'uv sync' to install locked deps.%RESET%
    type "%TEMP%\walmart_pyspark_ver.txt"
    call :stage_fail "Preflight failed" "Preflight"
    call :print_summary
    popd
    exit /b 1
)

REM Check prefix 3.5
echo !PYSPARK_VER! | findstr /b "3.5" >nul
if errorlevel 1 (
    echo %RED% PySpark !PYSPARK_VER! is incompatible; this project requires 3.5.x. Run 'uv sync' to restore locked version.%RESET%
    call :stage_fail "Preflight failed — PySpark !PYSPARK_VER! requires 3.5.x" "Preflight"
    call :print_summary
    popd
    exit /b 1
)
echo %GREEN% PySpark !PYSPARK_VER! OK%RESET%
call :log "INFO" "Preflight passed: PySpark !PYSPARK_VER!"
call :stage_pass "Preflight completed" "Preflight"

REM =========================================================================
REM STAGE 1 — EXTRACT
REM =========================================================================
call :stage_header "1" "EXTRACT (MongoDB to Bronze)"
uv run python scripts/python/extract.py %EXTRACT_ARGS%
if errorlevel 1 (
    call :stage_fail "Extract failed. Stopping pipeline. See logs/ for detail." "Extract"
    call :print_summary
    popd
    exit /b 1
)
call :stage_pass "Extract completed" "Extract"

REM =========================================================================
REM STAGE 2 — BRONZE SQL TESTS
REM =========================================================================
call :stage_header "2" "BRONZE SQL TESTS"
uv run python scripts/python/sql_test.py tests/bronze
if errorlevel 1 (
    call :stage_fail "Bronze Tests failed. Stopping pipeline." "Bronze Tests"
    call :print_summary
    popd
    exit /b 1
)
call :stage_pass "Bronze Tests completed" "Bronze Tests"

REM =========================================================================
REM STAGE 3 — DBT SILVER (build + test)
REM =========================================================================
call :stage_header "3" "DBT SILVER (build and test)"
pushd "%DBT_DIR%"
uv run dbt run --select silver
if errorlevel 1 (
    popd
    call :stage_fail "dbt silver build failed. Stopping pipeline." "Silver dbt"
    call :print_summary
    popd
    exit /b 1
)
uv run dbt test --select silver
if errorlevel 1 (
    popd
    call :stage_fail "dbt silver tests failed. Stopping pipeline." "Silver dbt"
    call :print_summary
    popd
    exit /b 1
)
popd
call :stage_pass "Silver dbt completed" "Silver dbt"

REM =========================================================================
REM STAGE 4 — SILVER SQL TESTS
REM =========================================================================
call :stage_header "4" "SILVER SQL TESTS"
uv run python scripts/python/sql_test.py tests/silver
if errorlevel 1 (
    call :stage_fail "Silver Tests failed. Stopping pipeline." "Silver Tests"
    call :print_summary
    popd
    exit /b 1
)
call :stage_pass "Silver Tests completed" "Silver Tests"

REM =========================================================================
REM STAGE 5 — DBT GOLD (build + test)
REM =========================================================================
call :stage_header "5" "DBT GOLD (build and test)"
pushd "%DBT_DIR%"
uv run dbt run --select gold
if errorlevel 1 (
    popd
    call :stage_fail "dbt gold build failed. Stopping pipeline." "Gold dbt"
    call :print_summary
    popd
    exit /b 1
)
uv run dbt test --select gold
if errorlevel 1 (
    popd
    call :stage_fail "dbt gold tests failed. Stopping pipeline." "Gold dbt"
    call :print_summary
    popd
    exit /b 1
)
popd
call :stage_pass "Gold dbt completed" "Gold dbt"

REM =========================================================================
REM STAGE 6 — GOLD SQL TESTS
REM =========================================================================
call :stage_header "6" "GOLD SQL TESTS"
uv run python scripts/python/sql_test.py tests/gold
if errorlevel 1 (
    call :stage_fail "Gold Tests failed. Stopping pipeline." "Gold Tests"
    call :print_summary
    popd
    exit /b 1
)
call :stage_pass "Gold Tests completed" "Gold Tests"

REM =========================================================================
REM STAGE 7 — GREAT EXPECTATIONS
REM =========================================================================
call :stage_header "7" "GREAT EXPECTATIONS TESTS (Bronze, Silver, Gold)"
uv run python -m pipeline.data_quality.run --layer all
if errorlevel 1 (
    call :stage_fail "Great Expectations failed. Stopping pipeline." "Great Expectations"
    call :print_summary
    popd
    exit /b 1
)
call :stage_pass "Great Expectations completed" "Great Expectations"

REM ---- Success --------------------------------------------------------------
call :log "INFO" "Pipeline completed successfully"
call :print_summary
echo.
echo %GREEN%%BOLD% PIPELINE COMPLETE — all 8 stages passed.%RESET%
popd
exit /b 0
