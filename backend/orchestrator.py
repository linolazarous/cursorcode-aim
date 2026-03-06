"""
CursorCode AI - Advanced Orchestrator
Features:
- Multi-agent AI pipeline
- Memory-aware generation
- Code execution sandbox
- Parallel agent execution
- SSE streaming
- Self-deploying project previews
"""

import os
import asyncio
import logging
import subprocess
from typing import AsyncGenerator, List, Dict

import httpx
from sse_starlette.sse import EventSourceResponse  # <-- updated import

# Changed from 'from backend.ai_memory import AIMemory' to relative import
from .ai_memory import AIMemory
from .code_executor import execute_code

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL", "grok-4-latest")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MEMORY_DB = os.getenv("MEMORY_DB", "cursorcode_ai")

memory = AIMemory(MONGO_URL, MEMORY_DB)

# Shared HTTP Client
client = httpx.AsyncClient(timeout=90.0)

# ---------------------------------------------------
# Core Grok Call
# ---------------------------------------------------
async def call_grok(
    api_key: str,
    model: str,
    messages: List[Dict],
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        response = await client.post(
            XAI_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPError as e:
        logger.error(f"Grok API error: {e}")
        raise Exception("AI request failed")

# ---------------------------------------------------
# Agent Prompts
# ---------------------------------------------------
AGENT_PROMPTS = {
    "architect": "Design scalable architecture for the user's project including tech stack, database, APIs, and deployment strategy.",
    "frontend": "Generate modern frontend UI code using Next.js, React, and Tailwind. Focus on performance and responsive design.",
    "backend": "Generate secure backend APIs using FastAPI. Include authentication, database models, and endpoints.",
    "security": "Analyze code and architecture for vulnerabilities. Suggest security improvements and best practices.",
    "qa": "Generate automated tests using pytest and integration tests.",
    "devops": "Generate deployment configuration including Docker, CI/CD, and cloud deployment steps."
}

# ---------------------------------------------------
# Run Agent
# ---------------------------------------------------
async def run_agent(
    api_key: str,
    agent: str,
    user_prompt: str,
    context: str = "",
) -> str:
    if agent not in AGENT_PROMPTS:
        raise ValueError(f"Unknown agent: {agent}")

    logger.info(f"Running agent: {agent}")
    system = AGENT_PROMPTS[agent]
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"User request:\n{user_prompt}\n\nContext:\n{context}"}
    ]
    return await call_grok(api_key, DEFAULT_MODEL, messages)

# ---------------------------------------------------
# Deploy Preview
# ---------------------------------------------------
async def deploy_preview(project_name: str, frontend_path: str, backend_path: str) -> str:
    """
    Deploy project to a live preview domain using docker-compose and Nginx/Traefik.
    """
    domain = f"{project_name}.cursorcode.ai.app"
    try:
        subprocess.run(["docker-compose", "-f", f"{frontend_path}/docker-compose.yml", "up", "-d"], check=True)
        subprocess.run(["docker-compose", "-f", f"{backend_path}/docker-compose.yml", "up", "-d"], check=True)
        subprocess.run(["nginx", "-s", "reload"], check=True)
        return f"https://{domain}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: {e}")
        return "Deployment failed"

# ---------------------------------------------------
# Main Orchestration Pipeline
# ---------------------------------------------------
async def orchestrate_project(api_key: str, prompt: str, user_email: str) -> Dict:
    logger.info("Starting orchestration pipeline")

    # Inject AI memory
    memory_context = memory.build_context(user_email)
    full_prompt = prompt + "\n\n" + memory_context

    # Architecture
    architecture = await run_agent(api_key, "architect", full_prompt)

    # Parallel frontend + backend
    frontend_task = run_agent(api_key, "frontend", prompt, architecture)
    backend_task = run_agent(api_key, "backend", prompt, architecture)
    frontend, backend = await asyncio.gather(frontend_task, backend_task)

    # Sandbox backend execution
    execution_result = execute_code(backend, "python")
    execution_log = f"Execution Success: {execution_result['success']}\nOutput:\n{execution_result['output']}\nError:\n{execution_result['error']}"

    # Security
    security = await run_agent(api_key, "security", prompt, frontend + "\n\n" + backend)

    # QA
    tests = await run_agent(api_key, "qa", prompt, backend)

    # DevOps
    devops = await run_agent(api_key, "devops", prompt, backend)

    # Store in memory
    memory.store_memory(user_email, prompt, architecture, frontend, backend)

    # Deploy preview
    preview_url = await deploy_preview(
        project_name=prompt[:20].replace(" ", "-").lower(),
        frontend_path="./temp_projects/frontend",
        backend_path="./temp_projects/backend"
    )

    return {
        "architecture": architecture,
        "frontend": frontend,
        "backend": backend,
        "security": security,
        "tests": tests,
        "devops": devops,
        "execution_log": execution_log,
        "preview_url": preview_url
    }

# ---------------------------------------------------
# Streaming SSE Orchestration
# ---------------------------------------------------
async def stream_orchestration_sse(
    project_id: str,
    prompt: str,
    api_key: str,
    user_email: str
) -> EventSourceResponse:

    async def event_generator() -> AsyncGenerator[str, None]:
        logger.info(f"Streaming orchestration started for {project_id}")
        yield "Starting orchestration...\n"

        context = memory.build_context(user_email)
        agents = ["architect", "frontend", "backend", "security", "qa", "devops"]

        for agent in agents:
            yield f"Running {agent} agent...\n"
            try:
                result = await run_agent(api_key, agent, prompt, context)
                context += "\n\n" + result[:2000]
                yield f"{agent} completed\n"
                yield result + "\n"
            except Exception as e:
                logger.error(f"{agent} failed: {e}")
                yield f"{agent} failed\n"
            await asyncio.sleep(0.5)

        yield "[COMPLETE] Project generated\n"

    return EventSourceResponse(event_generator())
