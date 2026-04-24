"""
Safely executes Python code in a subprocess with a hard timeout.
Output is fed back into explanations so the LLM references real runtime behavior.
Only used for Python — other languages are statically analyzed only.
"""

import subprocess
import tempfile
import os
from typing import Dict


TIMEOUT_SECONDS = 5

# These keywords trigger an instant rejection before any subprocess is created
BLOCKED_PATTERNS = [
    "import os", "import sys", "import subprocess",
    "import socket", "import requests", "import urllib",
    "__import__", "eval(", "exec(", "open(",
    "shutil", "pathlib", "glob",
]


def run_python(code: str) -> Dict:
    """
    Runs Python code safely. Returns stdout, stderr, and return code.
    Blocks dangerous imports before execution.
    """
    # Safety check
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return {
                "stdout": "",
                "stderr": f"Blocked: '{pattern}' is not allowed in the sandbox.",
                "returncode": 1,
                "blocked": True,
            }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        return {
            "stdout": result.stdout[:2000],   # cap at 2000 chars
            "stderr": result.stderr[:500],
            "returncode": result.returncode,
            "blocked": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {TIMEOUT_SECONDS} seconds.",
            "returncode": 1,
            "blocked": False,
        }
    finally:
        os.unlink(tmp_path)
