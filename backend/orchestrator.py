"""
CursorCode AI - Autonomous Software Factory Orchestrator
Coordinates multi-agent AI project generation with memory, credits, and deployment.
"""

import os
import asyncio
import logging
import re
from typing import Dict

from ai_agents import run_agent
from ai_memory import AIMemory
from code_executor import execute_code
from ai_metrics import track_ai_usage
from ai_repo_builder import build_repository

logger = logging.getLogger("orchestrator")

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "cursorcode_ai")

# Safe memory init
memory = None
try:
    if MONGO_URL:
        memory = AIMemory(MONGO_URL, DB_NAME)
        logger.info("AI memory initialized")
except Exception as e:
    logger.warning(f"Memory disabled: {e}")

def clean_project_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    return name[:25]

async def orchestrate_project(api_key: str, prompt: str, user_email: str) -> Dict:
    logger.info(f"AI project generation started for {user_email}")
    project_name = clean_project_name(prompt)

    # Memory context
    memory_context = ""
    if memory:
        try:
            memory_context = memory.build_context(user_email)
        except Exception as e:
            logger.warning(f"Memory read failed: {e}")

    full_prompt = f"User Request:\n{prompt}\n\nPrevious Knowledge:\n{memory_context}"

    # Architect agent
    architecture = await asyncio.wait_for(
        run_agent(api_key, "architect", full_prompt), timeout=120
    )

    # Parallel frontend + backend
    frontend_task = asyncio.create_task(run_agent(api_key, "frontend", prompt, architecture))
    backend_task = asyncio.create_task(run_agent(api_key, "backend", prompt, architecture))
    frontend, backend = await asyncio.gather(frontend_task, backend_task)

    # Code execution test
    try:
        execution = execute_code(backend, language="python")
        execution_log = f"Success: {execution.get('success')}\nOutput:\n{execution.get('output')}\nError:\n{execution.get('error')}"
    except Exception as e:
        execution_log = f"Execution skipped: {str(e)}"

    # Security review
    security = await run_agent(api_key, "security", prompt, frontend + backend)

    # QA tests
    tests = await run_agent(api_key, "qa", prompt, backend)

    # DevOps
    devops = await run_agent(api_key, "devops", prompt, backend)

    # Store memory
    if memory:
        try:
            memory.store_memory(user_email, prompt, architecture, frontend, backend)
        except Exception as e:
            logger.warning(f"Memory store failed: {e}")

    # Build repository
    repo_result = build_repository(
        project_id=project_name,
        project_data={
            "frontend": frontend, "backend": backend,
            "tests": tests, "devops": devops, "architecture": architecture,
        }
    )

    return {
        "project_name": project_name,
        "architecture": architecture,
        "frontend": frontend,
        "backend": backend,
        "security": security,
        "tests": tests,
        "devops": devops,
        "execution_log": execution_log,
        "repository": repo_result,
    }
