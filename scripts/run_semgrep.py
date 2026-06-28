"""
scripts/run_semgrep.py
Pre-commit hook shim: runs Semgrep using the project's own .venv installation.
Works regardless of pre-commit's working directory changes.
"""
import os
import subprocess
import sys
from pathlib import Path

# Resolve project root relative to this script
project_root = Path(__file__).parent.parent.resolve()
semgrep_exe = project_root / ".venv" / "Scripts" / "semgrep.exe"
config = project_root / ".semgrep" / "sdd-safety-rules.yaml"

if not semgrep_exe.exists():
    # Fallback: try PATH
    semgrep_exe = "semgrep"

result = subprocess.run(
    [str(semgrep_exe), "scan", f"--config={config}", "--error"],
    cwd=str(project_root),
)
sys.exit(result.returncode)
