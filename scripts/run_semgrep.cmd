@echo off
REM Self-locating semgrep wrapper for pre-commit on Windows.
REM Works regardless of working directory because it resolves semgrep
REM relative to this script's own location (always at <project_root>/scripts/).
set "SCRIPT_DIR=%~dp0"
set "SEMGREP=%SCRIPT_DIR%..\\.venv\\Scripts\\semgrep.exe"
"%SEMGREP%" scan --config="%SCRIPT_DIR%..\.semgrep\sdd-safety-rules.yaml" --error
