"""
CursorCode AI - Deployment Routes
Uploads project files to Emergent Object Storage for real static hosting.
Falls back to simulation when storage is unavailable.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response

from core.database import db
from core.security import get_current_user, require_verified_email
from models.schemas import User, Deployment
from services.storage import (
    is_storage_available, upload_deployment_files, get_deployment_file
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["deployments"])


def _make_preview_url(request: Request, deployment_id: str) -> str:
    """Build the public preview URL for a deployment."""
    # Use the request's base URL to construct the preview link
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    return f"{scheme}://{host}/api/preview/{deployment_id}/index.html"


@router.post("/deploy/{project_id}")
async def deploy_project(project_id: str, request: Request, user: User = Depends(require_verified_email)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")

    files = project_doc.get("files", {})
    code_files = {k: v for k, v in files.items() if not k.startswith("_docs/")}
    if not code_files:
        raise HTTPException(status_code=400, detail="No files to deploy")

    project_name = project_doc['name'].lower().replace(' ', '-').replace('_', '-')
    project_name = ''.join(c for c in project_name if c.isalnum() or c == '-')[:30]
    subdomain = f"{project_name}-{project_id[:8]}"

    now = datetime.now(timezone.utc)
    logs = [f"[{now.isoformat()}] Deployment initiated for {project_doc['name']}"]

    # Check if real storage is available
    if is_storage_available():
        logs.append(f"[{now.isoformat()}] Uploading {len(code_files)} files to object storage...")

        # Ensure there's an index.html entry point
        if "index.html" not in code_files:
            code_files["index.html"] = _generate_index_html(project_doc, code_files)
            logs.append(f"[{now.isoformat()}] Generated index.html entry point")

        deployment = Deployment(
            project_id=project_id, user_id=user.id, subdomain=subdomain,
            status="deploying", url="", files={},
            logs=logs,
        )
        deployment_doc = deployment.model_dump()
        deployment_doc['created_at'] = deployment_doc['created_at'].isoformat()
        deployment_doc['updated_at'] = deployment_doc['updated_at'].isoformat()
        await db.deployments.insert_one(deployment_doc)

        try:
            result = upload_deployment_files(deployment.id, code_files)
            logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Uploaded {result['uploaded']}/{len(code_files)} files")

            if result["errors"] > 0:
                for err in result["error_details"][:3]:
                    logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Warning: {err['filename']}: {err['error']}")

            deployed_url = _make_preview_url(request, deployment.id)
            logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Deployment live at {deployed_url}")

            # Store file manifest (not content) in deployment
            file_manifest = {f["filename"]: f["storage_path"] for f in result["files"]}

            await db.deployments.update_one(
                {"id": deployment.id},
                {"$set": {
                    "status": "deployed",
                    "url": deployed_url,
                    "file_manifest": file_manifest,
                    "files_count": result["uploaded"],
                    "logs": logs,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )

            await db.projects.update_one(
                {"id": project_id},
                {"$set": {
                    "status": "deployed",
                    "deployed_url": deployed_url,
                    "deployment_id": deployment.id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )

            return {
                "deployment_id": deployment.id,
                "deployed_url": deployed_url,
                "subdomain": subdomain,
                "status": "deployed",
                "files_uploaded": result["uploaded"],
                "logs": logs,
            }

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Deployment failed: {str(e)}")
            await db.deployments.update_one(
                {"id": deployment.id},
                {"$set": {"status": "failed", "logs": logs, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

    else:
        # Fallback: simulation mode
        deployed_url = f"https://{subdomain}.cursorcode.app"
        logs.extend([
            f"[{now.isoformat()}] [DEMO] Storage not configured — running in simulation mode",
            f"[{now.isoformat()}] [DEMO] Simulated deployment at {deployed_url}",
        ])
        deployment = Deployment(
            project_id=project_id, user_id=user.id, subdomain=subdomain,
            status="deployed", url=deployed_url, files={},
            logs=logs,
        )
        deployment_doc = deployment.model_dump()
        deployment_doc['created_at'] = deployment_doc['created_at'].isoformat()
        deployment_doc['updated_at'] = deployment_doc['updated_at'].isoformat()
        await db.deployments.insert_one(deployment_doc)
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"status": "deployed", "deployed_url": deployed_url,
                      "deployment_id": deployment.id, "updated_at": now.isoformat()}}
        )
        return {
            "deployment_id": deployment.id,
            "deployed_url": deployed_url,
            "subdomain": subdomain,
            "status": "deployed",
            "demo": True,
            "logs": logs,
        }


# ==================== PREVIEW / FILE SERVING ====================

@router.get("/preview/{deployment_id}/{filepath:path}")
async def serve_deployment_file(deployment_id: str, filepath: str):
    """Serve a file from a deployed project (public, no auth required)."""
    deployment = await db.deployments.find_one(
        {"id": deployment_id, "status": "deployed"}, {"_id": 0}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if not is_storage_available():
        raise HTTPException(status_code=503, detail="Storage not configured — deployment is in simulation mode")

    try:
        data, content_type = get_deployment_file(deployment_id, filepath)
        return Response(content=data, media_type=content_type, headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        })
    except Exception as e:
        logger.error(f"File serve error: {deployment_id}/{filepath}: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")


# ==================== CRUD ====================

@router.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str, user: User = Depends(get_current_user)):
    deployment_doc = await db.deployments.find_one({"id": deployment_id, "user_id": user.id}, {"_id": 0})
    if not deployment_doc:
        raise HTTPException(status_code=404, detail="Deployment not found")
    deployment_doc.pop("files", None)  # Don't return file contents
    return deployment_doc


@router.get("/deployments")
async def list_deployments(user: User = Depends(get_current_user)):
    deployments = await db.deployments.find(
        {"user_id": user.id}, {"_id": 0, "files": 0}
    ).sort("created_at", -1).to_list(50)
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


# ==================== HELPERS ====================

def _generate_index_html(project: dict, files: dict) -> str:
    """Generate an index.html that links to all project files."""
    name = project.get("name", "Project")
    desc = project.get("description", "")

    # Check for common entry points
    for entry in ["App.jsx", "App.js", "app.jsx", "app.js", "main.py", "main.js"]:
        if entry in files:
            break

    file_links = ""
    for fname in sorted(files.keys()):
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        icon = {"py": "🐍", "js": "📜", "jsx": "⚛️", "ts": "📘", "tsx": "⚛️",
                "html": "🌐", "css": "🎨", "json": "📋", "md": "📝"}.get(ext, "📄")
        file_links += f'      <li><a href="{fname}">{icon} {fname}</a></li>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} - CursorCode AI</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0e1a; color: #e2e8f0; min-height: 100vh; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ font-size: 2rem; margin-bottom: 8px; background: linear-gradient(135deg, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .desc {{ color: #94a3b8; margin-bottom: 32px; }}
    .badge {{ display: inline-block; background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px 12px; font-size: 0.75rem; color: #60a5fa; margin-bottom: 24px; }}
    h2 {{ font-size: 1.1rem; color: #cbd5e1; margin-bottom: 16px; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }}
    ul {{ list-style: none; }}
    li {{ margin-bottom: 8px; }}
    a {{ color: #60a5fa; text-decoration: none; padding: 8px 12px; display: inline-block; border-radius: 6px; transition: background 0.2s; }}
    a:hover {{ background: #1e293b; }}
    .footer {{ margin-top: 48px; padding-top: 24px; border-top: 1px solid #1e293b; color: #475569; font-size: 0.8rem; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">Deployed with CursorCode AI</div>
    <h1>{name}</h1>
    <p class="desc">{desc}</p>
    <h2>Project Files</h2>
    <ul>
{file_links}    </ul>
    <div class="footer">
      Deployed by CursorCode AI &mdash; Autonomous Software Engineering Platform
    </div>
  </div>
</body>
</html>"""
