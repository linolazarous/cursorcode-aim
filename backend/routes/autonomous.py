"""
CursorCode AI - Autonomous AI Module Routes
Exposes guardrails, sandbox, validation loop, snapshot manager,
context pruning, dependency graph, and feedback collector.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request

from core.database import db
from core.security import get_current_user
from models.schemas import User
from services.stripe_service import check_credits
from ai_rate_limiter import check_rate_limit
from services import guardrails, sandbox, context_pruning, dependency_graph, feedback_collector
from services.snapshot_manager import (
    create_pre_op_snapshot, rollback_to_snapshot,
    list_snapshots as list_snap, get_snapshot_diff,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autonomous", tags=["autonomous"])


def _enforce(user: User, operation: str):
    if not check_rate_limit(user.id, user.plan):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    ok, cost, remaining = check_credits(user.credits, user.credits_used, operation)
    if not ok:
        raise HTTPException(status_code=402, detail=f"Insufficient credits ({remaining} remaining, {cost} needed)")
    return cost


# ==================== GUARDRAILS ====================

@router.post("/guardrails/validate")
async def validate_code(request: Request, user: User = Depends(get_current_user)):
    """Validate AI-generated code for lazy patterns, credential leaks, hallucinated libs."""
    data = await request.json()
    code = data.get("code", "")
    language = data.get("language", "python")
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    result = guardrails.validate_output(code, language)
    return result


@router.post("/guardrails/validate-project/{project_id}")
async def validate_project_files(project_id: str, user: User = Depends(get_current_user)):
    """Run guardrails on all files in a project."""
    project = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files", {})
    if not files:
        raise HTTPException(status_code=400, detail="No files in project")
    result = guardrails.validate_files(files)
    return result


# ==================== SANDBOX ====================

@router.post("/sandbox/execute")
async def execute_in_sandbox(request: Request, user: User = Depends(get_current_user)):
    """Execute code in a subprocess sandbox."""
    cost = _enforce(user, "sandbox_execution")
    data = await request.json()
    code = data.get("code", "")
    language = data.get("language", "python")
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    result = sandbox.run_sandboxed(code, language)
    # Deduct credits
    await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": cost}})
    result["credits_used"] = cost
    return result


@router.post("/sandbox/run-tests/{project_id}")
async def run_project_tests(project_id: str, user: User = Depends(get_current_user)):
    """Run test files in a project via sandbox."""
    cost = _enforce(user, "sandbox_execution")
    project = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files", {})
    result = sandbox.run_project_tests(files)
    await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": cost}})
    result["credits_used"] = cost
    return result


# ==================== VALIDATION LOOP ====================

@router.post("/validate-loop")
async def run_validation(request: Request, user: User = Depends(get_current_user)):
    """Run the test-gen -> execute -> debug validation loop on code."""
    cost = _enforce(user, "debug")
    data = await request.json()
    code = data.get("code", "")
    filename = data.get("filename", "main.py")
    language = data.get("language", "python")
    max_iterations = min(data.get("max_iterations", 3), 5)
    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    # Pre-op snapshot if project_id provided
    project_id = data.get("project_id")
    if project_id:
        await create_pre_op_snapshot(project_id, user.id, "validation_loop")

    from services.validation_loop import run_validation_loop
    result = await run_validation_loop(code, filename, language, max_iterations)
    await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": cost}})
    result["credits_used"] = cost
    return result


# ==================== SNAPSHOT MANAGER ====================

@router.post("/snapshots/{project_id}/auto")
async def create_auto_snapshot(project_id: str, request: Request, user: User = Depends(get_current_user)):
    """Create a pre-operation snapshot."""
    data = await request.json()
    operation = data.get("operation", "manual")
    snapshot_id = await create_pre_op_snapshot(project_id, user.id, operation)
    if not snapshot_id:
        raise HTTPException(status_code=400, detail="Could not create snapshot (project not found or no files)")
    return {"snapshot_id": snapshot_id, "operation": operation}


@router.post("/snapshots/{project_id}/rollback/{snapshot_id}")
async def rollback_snapshot(project_id: str, snapshot_id: str, user: User = Depends(get_current_user)):
    """Rollback project to a snapshot (auto-saves current state first)."""
    result = await rollback_to_snapshot(project_id, user.id, snapshot_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Rollback failed"))
    return result


@router.get("/snapshots/{project_id}")
async def get_snapshots(project_id: str, include_auto: bool = True, user: User = Depends(get_current_user)):
    """List snapshots for a project."""
    snapshots = await list_snap(project_id, user.id, include_auto)
    return {"snapshots": snapshots}


@router.get("/snapshots/{project_id}/diff/{snapshot_id}")
async def snapshot_diff(project_id: str, snapshot_id: str, user: User = Depends(get_current_user)):
    """Compare a snapshot with current project state."""
    result = await get_snapshot_diff(project_id, user.id, snapshot_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== CONTEXT PRUNING ====================

@router.post("/context/rank/{project_id}")
async def rank_project_files(project_id: str, request: Request, user: User = Depends(get_current_user)):
    """Rank project files by relevance to a prompt."""
    data = await request.json()
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    project = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files", {})
    ranked = context_pruning.rank_files_by_relevance(files, prompt)
    return {"ranked_files": ranked}


@router.post("/context/prune/{project_id}")
async def prune_project_context(project_id: str, request: Request, user: User = Depends(get_current_user)):
    """Select files that fit within a token budget, ranked by relevance."""
    data = await request.json()
    prompt = data.get("prompt", "")
    token_budget = data.get("token_budget", 12000)
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    project = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files", {})
    result = context_pruning.prune_context(files, prompt, token_budget)
    # Remove file contents from response to keep it lightweight
    result.pop("selected_files", None)
    return result


# ==================== DEPENDENCY GRAPH ====================

@router.get("/deps/{project_id}")
async def get_dependency_graph(project_id: str, user: User = Depends(get_current_user)):
    """Build and return the dependency graph for a project."""
    project = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files", {})
    graph = dependency_graph.build_dependency_graph(files)
    return graph


@router.post("/deps/{project_id}/affected")
async def get_affected_by_change(project_id: str, request: Request, user: User = Depends(get_current_user)):
    """Find all downstream files affected by a change to a specific file."""
    data = await request.json()
    changed_file = data.get("changed_file", "")
    if not changed_file:
        raise HTTPException(status_code=400, detail="changed_file is required")
    project = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files", {})
    result = dependency_graph.get_affected_files(files, changed_file)
    return result


# ==================== FEEDBACK COLLECTOR ====================

@router.post("/feedback")
async def submit_user_feedback(request: Request, user: User = Depends(get_current_user)):
    """Submit feedback on AI-generated output."""
    data = await request.json()
    rating = data.get("rating")
    if rating is None:
        raise HTTPException(status_code=400, detail="rating is required (1-5)")
    result = await feedback_collector.submit_feedback(
        user_id=user.id,
        project_id=data.get("project_id", ""),
        rating=int(rating),
        feedback_type=data.get("type", "general"),
        comment=data.get("comment", ""),
        agent=data.get("agent"),
        file_name=data.get("file_name"),
        metadata=data.get("metadata"),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/feedback/stats")
async def get_feedback_statistics(project_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get aggregated feedback statistics."""
    return await feedback_collector.get_feedback_stats(project_id)


@router.get("/feedback/recent")
async def get_recent_user_feedback(project_id: Optional[str] = None, limit: int = 20, user: User = Depends(get_current_user)):
    """Get recent feedback entries."""
    return await feedback_collector.get_recent_feedback(project_id, limit)
