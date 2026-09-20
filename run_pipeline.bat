@echo off
REM Thin wrapper at repo root — forwards to pipeline\run_pipeline.bat
REM Allows double-click or: run_pipeline.bat [--dry-run] [--tables ...]
setlocal
set "ROOT=%~dp0"
call "%ROOT%pipeline\run_pipeline.bat" %*
exit /b %ERRORLEVEL%
