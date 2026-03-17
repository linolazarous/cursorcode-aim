"""
CursorCode AI - AI Planning Engine
Breaks user requests into structured development tasks.
"""

import logging
from typing import Dict, Any
from ai_agents import call_grok

logger = logging.getLogger("ai_planner")

PLANNER_PROMPT = """You are a senior software architect and project planner.
Break the user request into a structured JSON development plan:
{"tasks": [{"id": 1, "name": "...", "description": "..."}, ...]}
Focus on: architecture, backend, frontend, testing, deployment."""

async def generate_plan(api_key: str, model: str, prompt: str) -> Dict[str, Any]:
    logger.info("Generating AI development plan")
    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        result = await call_grok(api_key=api_key, model=model, messages=messages)
        import json
        try:
            return {"plan": json.loads(result)}
        except Exception:
            return {"plan": result}
    except Exception as e:
        logger.error(f"Planner failed: {e}")
        return {"error": "planner_failed"}
