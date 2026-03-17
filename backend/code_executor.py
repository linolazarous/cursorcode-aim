"""
CursorCode AI - Secure Code Execution Sandbox
Supports: Python, Node.js
"""

import subprocess
import tempfile
import os
import logging
import shutil

logger = logging.getLogger("code_executor")

EXECUTION_TIMEOUT = 15
MAX_OUTPUT_SIZE = 10000

def _run_command(command, file_path):
    try:
        result = subprocess.run(
            command, capture_output=True, text=True,
            timeout=EXECUTION_TIMEOUT, cwd=os.path.dirname(file_path),
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout[:MAX_OUTPUT_SIZE],
            "error": result.stderr[:MAX_OUTPUT_SIZE],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Execution timed out"}
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return {"success": False, "output": "", "error": str(e)}

def run_python(code: str):
    sandbox_dir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(sandbox_dir, "main.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return _run_command(["python3", file_path], file_path)
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)

def run_node(code: str):
    sandbox_dir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(sandbox_dir, "main.js")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return _run_command(["node", file_path], file_path)
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)

def execute_code(code: str, language: str = "python"):
    language = language.lower()
    if not code or len(code.strip()) == 0:
        return {"success": False, "output": "", "error": "No code provided"}
    if language == "python":
        return run_python(code)
    if language in ["node", "javascript", "js"]:
        return run_node(code)
    return {"success": False, "output": "", "error": f"Unsupported language: {language}"}
