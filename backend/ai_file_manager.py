"""
CursorCode AI
File Manager

Handles AI generated project files safely.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger("ai_file_manager")


class FileManager:

    def __init__(self, base_dir="generated_projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def project_path(self, project_id: str):
        path = self.base_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_file(self, project_id: str, file_path: str, content: str):

        try:
            project_dir = self.project_path(project_id)
            full_path = project_dir / file_path

            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"File created: {full_path}")

            return str(full_path)

        except Exception as e:
            logger.error(f"File creation failed: {e}")
            return None

    def read_file(self, project_id: str, file_path: str):

        try:
            full_path = self.project_path(project_id) / file_path

            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()

        except Exception as e:
            logger.error(f"Read failed: {e}")
            return None

    def delete_file(self, project_id: str, file_path: str):

        try:
            full_path = self.project_path(project_id) / file_path
            os.remove(full_path)

            logger.info(f"Deleted file: {full_path}")

            return True

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
