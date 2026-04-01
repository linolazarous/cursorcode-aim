import uuid
import secrets
import logging
import zipfile
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from core.config import FRONTEND_URL
from core.database import db
from core.security import get_current_user, project_to_response
from models.schemas import User, Project, ProjectCreate, ProjectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


async def log_activity(project_id: str, user_id: str, action: str, detail: str = ""):
    activity = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user_id,
        "action": action,
        "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_activities.insert_one(activity)


@router.post("", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, user: User = Depends(get_current_user)):
    project = Project(user_id=user.id, name=project_data.name,
                      description=project_data.description or "", prompt=project_data.prompt or "")
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.projects.insert_one(doc)
    return project_to_response(project)


@router.get("", response_model=List[ProjectResponse])
async def get_projects(user: User = Depends(get_current_user)):
    projects = await db.projects.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    result = []
    for p in projects:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
        if isinstance(p.get('updated_at'), str):
            p['updated_at'] = datetime.fromisoformat(p['updated_at'])
        result.append(project_to_response(Project(**p)))
    return result


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if isinstance(project_doc.get('created_at'), str):
        project_doc['created_at'] = datetime.fromisoformat(project_doc['created_at'])
    if isinstance(project_doc.get('updated_at'), str):
        project_doc['updated_at'] = datetime.fromisoformat(project_doc['updated_at'])
    return project_to_response(Project(**project_doc))


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_data: ProjectCreate, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    update_data = {
        "name": project_data.name, "description": project_data.description or "",
        "prompt": project_data.prompt or "", "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.projects.update_one({"id": project_id}, {"$set": update_data})
    updated_doc = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if isinstance(updated_doc.get('created_at'), str):
        updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
    if isinstance(updated_doc.get('updated_at'), str):
        updated_doc['updated_at'] = datetime.fromisoformat(updated_doc['updated_at'])
    return project_to_response(Project(**updated_doc))


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: User = Depends(get_current_user)):
    result = await db.projects.delete_one({"id": project_id, "user_id": user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}


@router.put("/{project_id}/files")
async def update_project_files(project_id: str, files: Dict[str, str], user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"files": files, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Files updated"}


# ==================== SHARE ====================

@router.post("/{project_id}/share")
async def toggle_share(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    is_public = not project_doc.get("is_public", False)
    share_id = project_doc.get("share_id") or secrets.token_urlsafe(12)
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"is_public": is_public, "share_id": share_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await log_activity(project_id, user.id, "shared" if is_public else "unshared", f"Project {'shared publicly' if is_public else 'set to private'}")
    return {"is_public": is_public, "share_id": share_id, "share_url": f"{FRONTEND_URL}/shared/{share_id}"}


# ==================== EXPORT ====================

@router.get("/{project_id}/export")
async def export_project(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project_doc.get("files", {})
    if not files:
        raise HTTPException(status_code=400, detail="No files to export")
    buf = BytesIO()
    project_name = project_doc["name"].replace(" ", "-").lower()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(f"{project_name}/{fname}", content)
        readme = f"# {project_doc['name']}\n\n{project_doc.get('description', '')}\n\nGenerated by CursorCode AI\n"
        zf.writestr(f"{project_name}/README.md", readme)
    buf.seek(0)
    await log_activity(project_id, user.id, "exported", f"Project exported as ZIP ({len(files)} files)")
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{project_name}.zip"'})


# ==================== ACTIVITY ====================

@router.get("/{project_id}/activity")
async def get_project_activity(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    activities = await db.project_activities.find({"project_id": project_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return activities


# ==================== SNAPSHOTS ====================

@router.post("/{project_id}/snapshots")
async def create_snapshot(project_id: str, data: Dict[str, Any], user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    count = await db.project_snapshots.count_documents({"project_id": project_id})
    snapshot = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user.id,
        "label": data.get("label", f"Snapshot #{count + 1}"),
        "files": project_doc.get("files", {}),
        "file_count": len(project_doc.get("files", {})),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_snapshots.insert_one(snapshot)
    await log_activity(project_id, user.id, "snapshot", f"Created snapshot: {snapshot['label']}")
    return {"id": snapshot["id"], "label": snapshot["label"], "file_count": snapshot["file_count"], "created_at": snapshot["created_at"]}


@router.get("/{project_id}/snapshots")
async def list_snapshots(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    snapshots = await db.project_snapshots.find(
        {"project_id": project_id}, {"_id": 0, "files": 0}
    ).sort("created_at", -1).to_list(50)
    return snapshots


@router.post("/{project_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(project_id: str, snapshot_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    snapshot = await db.project_snapshots.find_one({"id": snapshot_id, "project_id": project_id}, {"_id": 0})
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    count = await db.project_snapshots.count_documents({"project_id": project_id})
    auto_snapshot = {
        "id": str(uuid.uuid4()), "project_id": project_id, "user_id": user.id,
        "label": f"Auto-save before restore #{count + 1}",
        "files": project_doc.get("files", {}),
        "file_count": len(project_doc.get("files", {})),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_snapshots.insert_one(auto_snapshot)
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"files": snapshot["files"], "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await log_activity(project_id, user.id, "restored", f"Restored from: {snapshot.get('label', 'unknown')}")
    return {"message": f"Restored from: {snapshot.get('label')}", "file_count": len(snapshot.get("files", {}))}


# ==================== MESSAGES ====================

@router.get("/{project_id}/messages")
async def get_project_messages(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    messages = await db.project_messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return messages


@router.post("/{project_id}/messages")
async def save_project_message(project_id: str, data: Dict[str, Any], user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    message = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "type": data.get("type", "user"),
        "content": data.get("content", ""),
        "agent": data.get("agent"),
        "label": data.get("label"),
        "status": data.get("status"),
        "files_count": data.get("files_count"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_messages.insert_one(message)
    return {"id": message["id"]}


@router.delete("/{project_id}/messages")
async def clear_project_messages(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.project_messages.delete_many({"project_id": project_id})
    return {"message": "Messages cleared"}
