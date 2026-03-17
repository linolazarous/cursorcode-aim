"""
CursorCode AI - Repository Builder
Constructs full project repositories from AI-generated code.
"""

import logging
from typing import Dict, List
from ai_file_manager import FileManager

logger = logging.getLogger("ai_repo_builder")
file_manager = FileManager()

def build_repository(project_id: str, project_data: Dict) -> Dict:
    logger.info(f"Building repository for {project_id}")
    created_files: List[str] = []
    try:
        for key, path in [("backend", "backend/main.py"), ("frontend", "frontend/app.jsx"),
                          ("tests", "tests/test_app.py"), ("devops", "Dockerfile"),
                          ("architecture", "ARCHITECTURE.md")]:
            if project_data.get(key):
                file_manager.create_file(project_id, path, project_data[key])
                created_files.append(path)

        readme = (f"# {project_id}\n\nGenerated with **CursorCode AI**\n\n"
                  "## Structure\n- frontend/\n- backend/\n- tests/\n- Dockerfile\n")
        file_manager.create_file(project_id, "README.md", readme)
        created_files.append("README.md")
    except Exception as e:
        logger.error(f"Error building repository: {e}")
    return {"project_id": project_id, "created_files": created_files}
