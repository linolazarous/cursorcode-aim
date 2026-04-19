"""
CursorCode AI - Code Execution Sandbox Service
Subprocess-based sandboxed execution with timeout and output limits.
Wraps code_executor.py with additional security and project-aware execution.
"""

import logging
from typing import Dict, List, Optional
from code_executor import execute_code
from ai_security import AISecurity
from services.guardrails import detect_credential_leaks

logger = logging.getLogger("sandbox")

MAX_CODE_LENGTH = 50_000
SUPPORTED_LANGUAGES = ["python", "javascript", "js", "node"]


def run_sandboxed(code: str, language: str = "python") -> Dict:
    """Execute code in a subprocess sandbox with security checks."""
    if not code or not code.strip():
        return {"success": False, "output": "", "error": "No code provided", "blocked": False}

    if len(code) > MAX_CODE_LENGTH:
        return {"success": False, "output": "", "error": f"Code too large ({len(code)} chars, max {MAX_CODE_LENGTH})", "blocked": True}

    language = language.lower()
    if language not in SUPPORTED_LANGUAGES:
        return {"success": False, "output": "", "error": f"Unsupported language: {language}. Supported: {SUPPORTED_LANGUAGES}", "blocked": True}

    # Security: check for dangerous patterns
    if not AISecurity.validate_prompt(code):
        return {"success": False, "output": "", "error": "Code contains blocked patterns (dangerous operations detected)", "blocked": True}

    # Security: check for credential leaks
    cred_issues = detect_credential_leaks(code)
    if cred_issues:
        return {"success": False, "output": "", "error": f"Code contains embedded credentials: {cred_issues[0]['description']}", "blocked": True}

    # Execute
    result = execute_code(code, language)
    result["blocked"] = False
    result["language"] = language
    return result


def run_project_tests(files: Dict[str, str]) -> Dict:
    """Run test files found in a project."""
    test_results = []
    test_files = {k: v for k, v in files.items()
                  if k.startswith("test_") or k.startswith("tests/") or "_test." in k}

    if not test_files:
        return {"tests_found": 0, "results": [], "summary": "No test files found"}

    for filename, code in test_files.items():
        lang = "python" if filename.endswith(".py") else "javascript"
        result = run_sandboxed(code, lang)
        test_results.append({
            "file": filename,
            "language": lang,
            **result,
        })

    passed = sum(1 for r in test_results if r["success"])
    return {
        "tests_found": len(test_files),
        "passed": passed,
        "failed": len(test_results) - passed,
        "results": test_results,
        "summary": f"{passed}/{len(test_results)} test files passed",
    }
