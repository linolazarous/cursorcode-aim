"""
CursorCode AI - Dependency Graph
Maps cross-file imports. Flags downstream files affected when a module changes.
"""

import re
import logging
from typing import Dict, List, Set

logger = logging.getLogger("dependency_graph")

# Import patterns by language
IMPORT_PATTERNS = {
    "python": [
        r"from\s+([\w.]+)\s+import",  # from module import ...
        r"^import\s+([\w.]+)",          # import module
    ],
    "javascript": [
        r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",  # import X from 'module'
        r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",      # require('module')
    ],
}


def _detect_language(filename: str) -> str:
    if filename.endswith(('.py',)):
        return "python"
    if filename.endswith(('.js', '.jsx', '.ts', '.tsx', '.mjs')):
        return "javascript"
    return "unknown"


def _normalize_import(raw_import: str, filename: str, language: str) -> str:
    """Normalize import path to a filename-like key."""
    raw = raw_import.strip()
    if language == "python":
        # Convert dots to slashes: core.config -> core/config.py
        return raw.replace('.', '/') + '.py'
    if language == "javascript":
        # Handle relative imports
        raw = raw.lstrip('./')
        if not any(raw.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.css']):
            raw += '.js'
        return raw
    return raw


def extract_imports(filename: str, code: str) -> List[str]:
    """Extract imported module references from a file."""
    language = _detect_language(filename)
    patterns = IMPORT_PATTERNS.get(language, [])
    imports = []

    for pattern in patterns:
        for match in re.finditer(pattern, code, re.MULTILINE):
            raw = match.group(1)
            normalized = _normalize_import(raw, filename, language)
            imports.append(normalized)

    return imports


def build_dependency_graph(files: Dict[str, str]) -> Dict:
    """Build a full dependency graph from project files."""
    # imports_map: file -> list of files it imports
    imports_map = {}
    # dependents_map: file -> list of files that import it
    dependents_map = {}

    all_filenames = set(files.keys())

    for filename, code in files.items():
        if filename.startswith("_docs/"):
            continue
        raw_imports = extract_imports(filename, code)

        resolved = []
        for imp in raw_imports:
            # Try to match against actual project files
            matched = None
            for proj_file in all_filenames:
                if proj_file.endswith(imp) or proj_file == imp:
                    matched = proj_file
                    break
                # Partial match (e.g., "config" matches "core/config.py")
                if imp.replace('/', '.').rstrip('.py') in proj_file.replace('/', '.'):
                    matched = proj_file
                    break
            if matched:
                resolved.append(matched)

        imports_map[filename] = resolved

        for dep in resolved:
            if dep not in dependents_map:
                dependents_map[dep] = []
            dependents_map[dep].append(filename)

    return {
        "imports": imports_map,
        "dependents": dependents_map,
        "file_count": len(imports_map),
    }


def get_affected_files(
    files: Dict[str, str],
    changed_file: str,
) -> Dict:
    """Given a changed file, find all downstream files affected."""
    graph = build_dependency_graph(files)
    dependents_map = graph["dependents"]

    affected: Set[str] = set()
    queue = [changed_file]

    while queue:
        current = queue.pop(0)
        for dep in dependents_map.get(current, []):
            if dep not in affected:
                affected.add(dep)
                queue.append(dep)

    return {
        "changed_file": changed_file,
        "directly_affected": dependents_map.get(changed_file, []),
        "all_affected": list(affected),
        "total_affected": len(affected),
    }
