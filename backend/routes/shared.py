import logging
from fastapi import APIRouter, HTTPException, Depends

from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shared"])


@router.get("/shared/{share_id}")
async def get_shared_project(share_id: str):
    project_doc = await db.projects.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found or not shared")
    await db.projects.update_one({"share_id": share_id}, {"$inc": {"view_count": 1}})
    owner = await db.users.find_one({"id": project_doc["user_id"]}, {"_id": 0, "name": 1})
    code_files = {k: v for k, v in project_doc.get("files", {}).items() if not k.startswith("_docs/")}
    return {
        "name": project_doc["name"],
        "description": project_doc["description"],
        "status": project_doc["status"],
        "files": code_files,
        "tech_stack": project_doc.get("tech_stack", []),
        "deployed_url": project_doc.get("deployed_url"),
        "view_count": project_doc.get("view_count", 0) + 1,
        "owner_name": owner.get("name", "Anonymous") if owner else "Anonymous",
        "created_at": project_doc.get("created_at", ""),
        "share_id": share_id,
    }
