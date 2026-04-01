import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends
import httpx

from core.database import db
from core.security import get_current_user, user_to_response
from models.schemas import User, UserResponse, UserUpdateRequest, GitHubRepo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


@router.put("/users/me", response_model=UserResponse)
async def update_user_profile(data: UserUpdateRequest, user: User = Depends(get_current_user)):
    update_fields = {}
    if data.name:
        update_fields["name"] = data.name
    if data.email and data.email != user.email:
        existing = await db.users.find_one({"email": data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_fields["email"] = data.email
    if update_fields:
        await db.users.update_one({"id": user.id}, {"$set": update_fields})
    updated_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    if isinstance(updated_doc.get('created_at'), str):
        updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
    return user_to_response(User(**updated_doc))


@router.post("/users/me/complete-onboarding")
async def complete_onboarding(user: User = Depends(get_current_user)):
    await db.users.update_one({"id": user.id}, {"$set": {"onboarding_completed": True}})
    return {"message": "Onboarding completed"}


# ==================== GITHUB REPOS ====================

@router.get("/github/repos", response_model=List[GitHubRepo])
async def get_github_repos(user: User = Depends(get_current_user)):
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub account not connected")
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {user.github_access_token}", "Accept": "application/vnd.github+json"},
                params={"per_page": 100, "sort": "updated", "direction": "desc"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch repositories")
            repos = response.json()
            return [
                GitHubRepo(
                    id=repo["id"], name=repo["name"], full_name=repo["full_name"],
                    description=repo.get("description"), html_url=repo["html_url"],
                    clone_url=repo["clone_url"], language=repo.get("language"),
                    stargazers_count=repo["stargazers_count"], forks_count=repo["forks_count"],
                    private=repo["private"], updated_at=repo["updated_at"]
                ) for repo in repos
            ]
    except httpx.HTTPError as e:
        logger.error(f"GitHub API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch repositories")


@router.post("/github/import/{repo_full_name:path}")
async def import_github_repo(repo_full_name: str, user: User = Depends(get_current_user)):
    from models.schemas import Project
    from core.security import project_to_response
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub account not connected")
    try:
        async with httpx.AsyncClient() as http_client:
            repo_response = await http_client.get(
                f"https://api.github.com/repos/{repo_full_name}",
                headers={"Authorization": f"Bearer {user.github_access_token}", "Accept": "application/vnd.github+json"}
            )
            if repo_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Repository not found")
            repo = repo_response.json()
            contents_response = await http_client.get(
                f"https://api.github.com/repos/{repo_full_name}/contents",
                headers={"Authorization": f"Bearer {user.github_access_token}", "Accept": "application/vnd.github+json"}
            )
            files = {}
            if contents_response.status_code == 200:
                contents = contents_response.json()
                code_extensions = ['.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css', '.json', '.md']
                for item in contents[:20]:
                    if item["type"] == "file" and any(item["name"].endswith(ext) for ext in code_extensions):
                        if item["size"] < 50000:
                            file_response = await http_client.get(
                                item["download_url"],
                                headers={"Authorization": f"Bearer {user.github_access_token}"}
                            )
                            if file_response.status_code == 200:
                                files[item["name"]] = file_response.text
        project = Project(
            user_id=user.id, name=repo["name"],
            description=repo.get("description") or f"Imported from GitHub: {repo_full_name}",
            prompt=f"Imported from GitHub: {repo['html_url']}",
            status="imported", files=files,
            tech_stack=[repo.get("language")] if repo.get("language") else [],
            github_repo=repo_full_name
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.projects.insert_one(doc)
        return project_to_response(project)
    except httpx.HTTPError as e:
        logger.error(f"GitHub import error: {e}")
        raise HTTPException(status_code=500, detail="Failed to import repository")
