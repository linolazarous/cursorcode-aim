"""
CursorCode AI
AI Planning Engine

Breaks user requests into structured development tasks
used by the orchestration system.
"""

import logging
from typing import List, Dict

from .ai_agents import call_grok

logger = logging.getLogger("ai_planner")


PLANNER_PROMPT = """
You are a senior software architect and project planner.

Break the user request into a structured development plan.

Return JSON with this format:

{
 "tasks": [
   {"id": 1, "name": "...", "description": "..."},
   {"id": 2, "name": "...", "description": "..."}
 ]
}

Rules:
- tasks must be sequential
- focus on real software development workflow
- include architecture, backend, frontend, testing, deployment
"""


async def generate_plan(api_key: str, model: str, prompt: str) -> Dict:
    """
    Generate structured development plan
    """

    logger.info("Generating AI development plan")

    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await call_grok(
            api_key=api_key,
            model=model,
            messages=messages,
        )

        return {
            "plan": result
        }

    except Exception as e:
        logger.error(f"Planner failed: {e}")
        return {"error": "planner_failed"}
