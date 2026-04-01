import uuid
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse

from core.config import DEFAULT_XAI_MODEL, FAST_REASONING_MODEL, FAST_NON_REASONING_MODEL
from core.database import db
from core.security import get_current_user, get_user_from_token_param
from models.schemas import User, AIGenerateRequest, AIGenerateResponse, CreditUsage
from services.ai import (
    select_model, calculate_credits, call_xai_api, parse_files_from_response,
    stream_xai_api, AGENT_CONFIGS
)
from routes.projects import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate", response_model=AIGenerateResponse)
async def generate_code(request: AIGenerateRequest, user: User = Depends(get_current_user)):
    model = request.model or select_model(request.task_type)
    credits_needed = calculate_credits(model, request.task_type)
    remaining_credits = user.credits - user.credits_used
    if remaining_credits < credits_needed:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    project_doc = await db.projects.find_one({"id": request.project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    system_message = """You are CursorCode AI, an elite autonomous AI software engineering system.
Generate clean, production-ready, well-documented code.
Output each file using this format:

```filename:ComponentName.jsx
// file content here
```

Always generate complete, working files with proper imports."""
    try:
        response = await call_xai_api(request.prompt, model, system_message)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        raise HTTPException(status_code=500, detail="AI generation failed")

    parsed_files = parse_files_from_response(response)
    if parsed_files:
        existing_files = project_doc.get("files", {})
        existing_files.update(parsed_files)
        await db.projects.update_one(
            {"id": request.project_id},
            {"$set": {"files": existing_files, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": credits_needed}})
    usage = CreditUsage(user_id=user.id, project_id=request.project_id, model=model,
                        credits_used=credits_needed, task_type=request.task_type)
    usage_doc = usage.model_dump()
    usage_doc['created_at'] = usage_doc['created_at'].isoformat()
    await db.credit_usage.insert_one(usage_doc)
    return AIGenerateResponse(
        id=str(uuid.uuid4()), project_id=request.project_id, prompt=request.prompt,
        response=response, model_used=model, credits_used=credits_needed,
        created_at=datetime.now(timezone.utc).isoformat(), files=parsed_files
    )


@router.get("/models")
async def get_ai_models():
    return {
        "models": [
            {"id": DEFAULT_XAI_MODEL, "name": "Grok 4 (Frontier)", "description": "Deep reasoning for architecture", "credits_per_use": 3},
            {"id": FAST_REASONING_MODEL, "name": "Grok 4 Fast Reasoning", "description": "Optimized for agentic workflows", "credits_per_use": 2},
            {"id": FAST_NON_REASONING_MODEL, "name": "Grok 4 Fast", "description": "High-throughput generation", "credits_per_use": 1}
        ]
    }


@router.get("/generate-stream")
async def generate_stream(
    request: Request,
    project_id: str,
    prompt: str,
    model: str = None,
):
    user = await get_user_from_token_param(request)
    model = model or FAST_REASONING_MODEL
    credits_needed = calculate_credits(model, "code_generation")
    remaining = user.credits - user.credits_used
    if remaining < credits_needed:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_stream():
        all_outputs = {}
        all_files = {}
        context_so_far = ""

        for agent_cfg in AGENT_CONFIGS:
            agent_name = agent_cfg["name"]
            agent_label = agent_cfg["label"]
            system_msg = agent_cfg["system"]

            yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent_name, 'label': agent_label})}\n\n"

            user_prompt = f"User Request:\n{prompt}\n"
            if context_so_far:
                user_prompt += f"\nPrevious agents' output (use as context):\n{context_so_far[:6000]}"

            full_response = ""
            try:
                async for chunk in stream_xai_api(user_prompt, model, system_msg):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'agent_chunk', 'agent': agent_name, 'content': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                yield f"data: {json.dumps({'type': 'agent_error', 'agent': agent_name, 'error': str(e)})}\n\n"
                full_response = f"// Agent {agent_name} encountered an error: {str(e)}"

            all_outputs[agent_name] = full_response
            context_so_far += f"\n\n--- {agent_label} Output ---\n{full_response[:3000]}"

            agent_files = parse_files_from_response(full_response)
            all_files.update(agent_files)

            yield f"data: {json.dumps({'type': 'agent_complete', 'agent': agent_name, 'files_count': len(agent_files)})}\n\n"

        existing_files = project_doc.get("files", {})
        existing_files.update(all_files)

        for agent_name, output in all_outputs.items():
            existing_files[f"_docs/{agent_name}_output.md"] = output

        await db.projects.update_one(
            {"id": project_id},
            {"$set": {
                "files": existing_files,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "generated",
            }}
        )

        await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": credits_needed}})
        usage = CreditUsage(user_id=user.id, project_id=project_id, model=model,
                            credits_used=credits_needed, task_type="multi_agent_build")
        usage_doc = usage.model_dump()
        usage_doc['created_at'] = usage_doc['created_at'].isoformat()
        await db.credit_usage.insert_one(usage_doc)

        yield f"data: {json.dumps({'type': 'complete', 'files': list(existing_files.keys()), 'credits_used': credits_needed})}\n\n"

        await log_activity(project_id, user.id, "ai_build", f"Multi-agent build: {len(existing_files)} files generated using {model}")

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
