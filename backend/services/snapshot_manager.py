"""
CursorCode AI - Snapshot Manager
Creates git-like snapshots before AI operations.
Enables 1-click rollback to any previous state.
Uses MongoDB project_snapshots collection (already exists).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List

from core.database import db

logger = logging.getLogger("snapshot_manager")


async def create_pre_op_snapshot(
    project_id: str,
    user_id: str,
    operation: str,
) -> Optional[str]:
    """Auto-create a snapshot before an AI operation. Returns snapshot ID."""
    project_doc = await db.projects.find_one(
        {"id": project_id, "user_id": user_id}, {"_id": 0}
    )
    if not project_doc:
        return None

    files = project_doc.get("files", {})
    if not files:
        return None

    snapshot_id = str(uuid.uuid4())
    snapshot = {
        "id": snapshot_id,
        "project_id": project_id,
        "user_id": user_id,
        "label": f"Auto-save before {operation}",
        "operation": operation,
        "auto": True,
        "files": files,
        "file_count": len(files),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_snapshots.insert_one(snapshot)
    logger.info(f"Pre-op snapshot created: {snapshot_id} for project {project_id}")
    return snapshot_id


async def rollback_to_snapshot(
    project_id: str,
    user_id: str,
    snapshot_id: str,
) -> Dict:
    """Restore project files from a snapshot. Auto-saves current state first."""
    project_doc = await db.projects.find_one(
        {"id": project_id, "user_id": user_id}, {"_id": 0}
    )
    if not project_doc:
        return {"success": False, "error": "Project not found"}

    snapshot = await db.project_snapshots.find_one(
        {"id": snapshot_id, "project_id": project_id}, {"_id": 0}
    )
    if not snapshot:
        return {"success": False, "error": "Snapshot not found"}

    # Auto-save current state before rollback
    current_files = project_doc.get("files", {})
    if current_files:
        await db.project_snapshots.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "user_id": user_id,
            "label": f"Auto-save before rollback to {snapshot.get('label', snapshot_id[:8])}",
            "operation": "rollback",
            "auto": True,
            "files": current_files,
            "file_count": len(current_files),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Restore
    restored_files = snapshot.get("files", {})
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "files": restored_files,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    logger.info(f"Rolled back project {project_id} to snapshot {snapshot_id}")
    return {
        "success": True,
        "snapshot_id": snapshot_id,
        "label": snapshot.get("label", ""),
        "files_restored": len(restored_files),
    }


async def list_snapshots(
    project_id: str,
    user_id: str,
    include_auto: bool = True,
    limit: int = 50,
) -> List[Dict]:
    """List snapshots for a project."""
    query = {"project_id": project_id}
    if not include_auto:
        query["auto"] = {"$ne": True}

    snapshots = await db.project_snapshots.find(
        query, {"_id": 0, "files": 0}
    ).sort("created_at", -1).to_list(limit)

    return snapshots


async def get_snapshot_diff(
    project_id: str,
    user_id: str,
    snapshot_id: str,
) -> Dict:
    """Compare a snapshot with current project state."""
    project_doc = await db.projects.find_one(
        {"id": project_id, "user_id": user_id}, {"_id": 0}
    )
    if not project_doc:
        return {"error": "Project not found"}

    snapshot = await db.project_snapshots.find_one(
        {"id": snapshot_id, "project_id": project_id}, {"_id": 0}
    )
    if not snapshot:
        return {"error": "Snapshot not found"}

    current_files = set(project_doc.get("files", {}).keys())
    snapshot_files = set(snapshot.get("files", {}).keys())

    added = list(current_files - snapshot_files)
    removed = list(snapshot_files - current_files)
    common = current_files & snapshot_files
    modified = [
        f for f in common
        if project_doc["files"].get(f) != snapshot["files"].get(f)
    ]

    return {
        "snapshot_id": snapshot_id,
        "snapshot_label": snapshot.get("label", ""),
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": len(common) - len(modified),
    }
