"""
CursorCode AI
Secure Code Execution Sandbox

Supports:
- Python
- Node.js

Used by QA agent to validate generated code.
"""

import subprocess
import tempfile
import os
import logging

logger = logging.getLogger("code_executor")


EXECUTION_TIMEOUT = 15


# =====================================================
# PYTHON EXECUTION
# =====================================================

def run_python(code: str):

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False
        ) as temp_file:

            temp_file.write(code)
            file_path = temp_file.name

        result = subprocess.run(
            ["python3", file_path],
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
        )

        output = result.stdout
        error = result.stderr

        os.remove(file_path)

        return {

            "success": result.returncode == 0,
            "output": output,
            "error": error,
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "output": "",
            "error": "Execution timed out",
        }


# =====================================================
# NODE EXECUTION
# =====================================================

def run_node(code: str):

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".js",
            delete=False
        ) as temp_file:

            temp_file.write(code)
            file_path = temp_file.name

        result = subprocess.run(
            ["node", file_path],
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
        )

        output = result.stdout
        error = result.stderr

        os.remove(file_path)

        return {

            "success": result.returncode == 0,
            "output": output,
            "error": error,
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "output": "",
            "error": "Execution timed out",
        }


# =====================================================
# UNIVERSAL EXECUTOR
# =====================================================

def execute_code(code: str, language: str = "python"):

    language = language.lower()

    if language == "python":

        return run_python(code)

    if language in ["node", "javascript", "js"]:

        return run_node(code)

    return {

        "success": False,
        "output": "",
        "error": f"Unsupported language: {language}",
    }
