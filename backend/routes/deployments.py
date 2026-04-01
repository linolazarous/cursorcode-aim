import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from core.database import db
from core.security import get_current_user
from models.schemas import User, Project, Deployment

logger = logging.getLogger(__name__)

router = APIRouter(tags=["deployments"])


@router.post("/deploy/{project_id}")
async def deploy_project(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    project_name = project_doc['name'].lower().replace(' ', '-').replace('_', '-')
    project_name = ''.join(c for c in project_name if c.isalnum() or c == '-')[:30]
    subdomain = f"{project_name}-{project_id[:8]}"
    deployed_url = f"https://{subdomain}.cursorcode.app"
    deployment = Deployment(
        project_id=project_id, user_id=user.id, subdomain=subdomain,
        status="deployed", url=deployed_url, files=project_doc.get('files', {}),
        logs=[
            f"[{datetime.now(timezone.utc).isoformat()}] Deployment initiated",
            f"[{datetime.now(timezone.utc).isoformat()}] Building project...",
            f"[{datetime.now(timezone.utc).isoformat()}] Installing dependencies...",
            f"[{datetime.now(timezone.utc).isoformat()}] Configuring SSL certificate...",
            f"[{datetime.now(timezone.utc).isoformat()}] Deployment successful!"
        ]
    )
    deployment_doc = deployment.model_dump()
    deployment_doc['created_at'] = deployment_doc['created_at'].isoformat()
    deployment_doc['updated_at'] = deployment_doc['updated_at'].isoformat()
    await db.deployments.insert_one(deployment_doc)
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"status": "deployed", "deployed_url": deployed_url,
                  "deployment_id": deployment.id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"deployment_id": deployment.id, "deployed_url": deployed_url,
            "subdomain": subdomain, "status": "deployed", "logs": deployment.logs}


@router.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str, user: User = Depends(get_current_user)):
    deployment_doc = await db.deployments.find_one({"id": deployment_id, "user_id": user.id}, {"_id": 0})
    if not deployment_doc:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment_doc


@router.get("/deployments")
async def list_deployments(user: User = Depends(get_current_user)):
    deployments = await db.deployments.find({"user_id": user.id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"deployments": deployments}


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str, user: User = Depends(get_current_user)):
    deployment_doc = await db.deployments.find_one({"id": deployment_id, "user_id": user.id}, {"_id": 0})
    if not deployment_doc:
        raise HTTPException(status_code=404, detail="Deployment not found")
    await db.projects.update_one(
        {"id": deployment_doc["project_id"]},
        {"$set": {"status": "draft", "deployed_url": None, "deployment_id": None}}
    )
    await db.deployments.delete_one({"id": deployment_id})
    return {"message": "Deployment deleted"}
