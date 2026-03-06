"""
CursorCode AI
Repository Builder

Constructs full project repositories from AI-generated code.
"""

import logging
from typing import Dict

from .ai_file_manager import FileManager

logger = logging.getLogger("ai_repo_builder")

file_manager = FileManager()


def build_repository(project_id: str, project_data: Dict):

    logger.info(f"Building repository for {project_id}")

    try:

        if "backend" in project_data:
            file_manager.create_file(
                project_id,
                "backend/main.py",
                project_data["backend"],
            )

        if "frontend" in project_data:
            file_manager.create_file(
                project_id,
                "frontend/app.jsx",
                project_data["frontend"],
            )

        if "tests" in project_data:
            file_manager.create_file(
                project_id,
                "tests/test_app.py",
                project_data["tests"],
            )

        if "devops" in project_data:
            file_manager.create_file(
                project_id,
                "Dockerfile",
                project_data["devops"],
            )

        if "architecture" in project_data:
            file_manager.create_file(
                project_id,
                "ARCHITECTURE.md",
                project_data["architecture"],
            )

        logger.info("Repository build complete")

        return {
            "status": "success",
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(f"Repository build failed: {e}")

        return {
            "status": "error",
            "message": str(e),
        }
