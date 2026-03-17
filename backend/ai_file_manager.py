"""
CursorCode AI - File Manager
Handles AI generated project files safely.
"""

import os
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger("ai_file_manager")

class FileManager:
    MAX_FILE_SIZE = 2_000_000

    def __init__(self, base_dir: str = "generated_projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if ".." in path.parts:
            raise ValueError("Invalid file path")
        return path

    def project_path(self, project_id: str) -> Path:
        safe_project = project_id.replace("/", "").replace("\\", "")
        path = self.base_dir / safe_project
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_file(self, project_id: str, file_path: str, content: str, overwrite: bool = True):
        try:
            project_dir = self.project_path(project_id)
            safe_path = self._sanitize_path(file_path)
            full_path = project_dir / safe_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if not overwrite and full_path.exists():
                return str(full_path)
            if len(content.encode("utf-8")) > self.MAX_FILE_SIZE:
                raise ValueError("File too large")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return str(full_path)
        except Exception as e:
            logger.error(f"File creation failed: {e}")
            return None

    def read_file(self, project_id: str, file_path: str):
        try:
            full_path = self.project_path(project_id) / self._sanitize_path(file_path)
            if not full_path.exists():
                return None
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Read failed: {e}")
            return None

    def list_files(self, project_id: str) -> List[str]:
        try:
            project_dir = self.project_path(project_id)
            return [
                str(Path(root, name).relative_to(project_dir))
                for root, _, filenames in os.walk(project_dir)
                for name in filenames
            ]
        except Exception as e:
            logger.error(f"List files failed: {e}")
            return []
