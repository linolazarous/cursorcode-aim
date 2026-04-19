"""
CursorCode AI - AI Guardrails
Blocks lazy code (comments/placeholders), detects hallucinated libraries,
prevents credential leaks, and validates AI output quality.
"""

import re
import logging
from typing import Dict, List

from ai_security import AISecurity

logger = logging.getLogger("guardrails")

# Common placeholder/lazy patterns that indicate incomplete code
LAZY_PATTERNS = [
    (r"#\s*TODO:?\s*implement", "TODO placeholder found"),
    (r"//\s*TODO:?\s*implement", "TODO placeholder found"),
    (r"pass\s*#", "Empty pass with comment"),
    (r"\.\.\.\s*#", "Ellipsis placeholder"),
    (r"raise\s+NotImplementedError", "NotImplementedError found"),
    (r"#\s*add\s+(your|the|actual|real)\s+", "Placeholder comment"),
    (r"//\s*add\s+(your|the|actual|real)\s+", "Placeholder comment"),
    (r"#\s*replace\s+with\s+", "Replace-with comment"),
    (r"#\s*insert\s+.+\s+here", "Insert-here comment"),
    (r"your[_-]?api[_-]?key", "Placeholder API key reference"),
    (r"placeholder", "Placeholder text found"),
    (r"lorem\s+ipsum", "Lorem ipsum text found"),
]

# Credential patterns that should never appear in generated code
CREDENTIAL_PATTERNS = [
    (r"sk[-_]live[-_][a-zA-Z0-9]{20,}", "Stripe live key detected"),
    (r"sk[-_]test[-_][a-zA-Z0-9]{20,}", "Stripe test key detected"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key detected"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub token detected"),
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key detected"),
    (r"mongodb\+srv://[^\s]+:[^\s]+@", "MongoDB URI with credentials"),
    (r"postgres://[^\s]+:[^\s]+@", "PostgreSQL URI with credentials"),
    (r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "JWT token detected"),
    (r"[a-f0-9]{40}", "Possible secret hash (40-char hex)"),
]

# Known non-existent or hallucinated libraries
HALLUCINATED_LIBS = {
    "python": [
        "fastapi_auth_plus", "react_python_bridge", "mongoengine_async",
        "django_fastapi", "flask_graphql_pro", "pydantic_ai",
        "auto_migrate", "smart_cache_pro", "pyreact", "fastapi_stripe_pro",
    ],
    "javascript": [
        "react-auto-state", "next-fastapi", "express-mongo-pro",
        "react-ai-components", "smart-form-builder", "auto-api-gen",
        "react-native-web-pro", "next-auth-plus", "express-gql-pro",
    ],
}


def detect_lazy_code(code: str) -> List[Dict]:
    """Detect placeholder comments and incomplete implementations."""
    issues = []
    for pattern, description in LAZY_PATTERNS:
        matches = list(re.finditer(pattern, code, re.IGNORECASE))
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            issues.append({
                "type": "lazy_code",
                "severity": "warning",
                "description": description,
                "line": line_num,
                "match": match.group()[:80],
            })
    return issues


def detect_credential_leaks(code: str) -> List[Dict]:
    """Scan for hardcoded credentials and secrets."""
    issues = []
    for pattern, description in CREDENTIAL_PATTERNS:
        matches = list(re.finditer(pattern, code))
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            issues.append({
                "type": "credential_leak",
                "severity": "critical",
                "description": description,
                "line": line_num,
                "match": match.group()[:20] + "***REDACTED***",
            })
    return issues


def detect_hallucinated_libs(code: str, language: str = "python") -> List[Dict]:
    """Detect imports of known non-existent libraries."""
    issues = []
    fake_libs = HALLUCINATED_LIBS.get(language, [])

    if language == "python":
        import_pattern = r"(?:from|import)\s+(\w+)"
    else:
        import_pattern = r"(?:import|require)\s*\(?['\"]([^'\"]+)"

    for match in re.finditer(import_pattern, code):
        lib_name = match.group(1).split('.')[0]
        if lib_name in fake_libs:
            line_num = code[:match.start()].count('\n') + 1
            issues.append({
                "type": "hallucinated_library",
                "severity": "error",
                "description": f"Non-existent library: {lib_name}",
                "line": line_num,
                "match": match.group()[:80],
            })
    return issues


def validate_output(code: str, language: str = "python") -> Dict:
    """Full guardrails validation on AI-generated code."""
    # Prompt safety check
    prompt_safe = AISecurity.validate_prompt(code)

    lazy_issues = detect_lazy_code(code)
    credential_issues = detect_credential_leaks(code)
    hallucination_issues = detect_hallucinated_libs(code, language)

    all_issues = lazy_issues + credential_issues + hallucination_issues
    critical = [i for i in all_issues if i["severity"] == "critical"]
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    passed = len(critical) == 0 and len(errors) == 0 and prompt_safe

    return {
        "passed": passed,
        "prompt_safe": prompt_safe,
        "total_issues": len(all_issues),
        "critical": len(critical),
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": all_issues,
        "sanitized_code": AISecurity.sanitize_code(code) if not prompt_safe else code,
    }


def validate_files(files: Dict[str, str]) -> Dict:
    """Validate all files in a project."""
    results = {}
    total_issues = 0
    all_passed = True

    for filename, content in files.items():
        if filename.startswith("_docs/"):
            continue
        lang = "javascript" if filename.endswith(('.js', '.jsx', '.ts', '.tsx')) else "python"
        result = validate_output(content, lang)
        results[filename] = result
        total_issues += result["total_issues"]
        if not result["passed"]:
            all_passed = False

    return {
        "all_passed": all_passed,
        "total_issues": total_issues,
        "files_checked": len(results),
        "results": results,
    }
