"""
CursorCode AI - Grok Orchestrator
Production-ready simplified orchestration engine
Compatible with xAI Grok API (2026)
"""

import os
import asyncio
import logging
from typing import AsyncGenerator, List, Dict

import httpx

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

XAI_API_URL = "https://api.x.ai/v1/chat/completions"

DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL", "grok-4-latest")

# ---------------------------------------------------
# Shared HTTP Client
# ---------------------------------------------------
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
    "architect": """
Design scalable architecture for the user's project.
Include tech stack, database, APIs, and deployment strategy.
""",

    "frontend": """
Generate modern frontend UI code using Next.js, React, and Tailwind.
Focus on performance and responsive design.
""",

    "backend": """
Generate secure backend APIs using FastAPI.
Include authentication, database models, and endpoints.
""",

    "security": """
Analyze code and architecture for vulnerabilities.
Suggest security improvements and best practices.
""",

    "qa": """
Generate automated tests using pytest and integration tests.
""",

    "devops": """
Generate deployment configuration including Docker, CI/CD,
and cloud deployment steps.
"""
}


# ---------------------------------------------------
# Agent Execution
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
        {"role": "user", "content": f"{user_prompt}\n\n{context}"},
    ]

    result = await call_grok(
        api_key=api_key,
        model=DEFAULT_MODEL,
        messages=messages,
    )

    return result


# ---------------------------------------------------
# Main Orchestration Pipeline
# ---------------------------------------------------
async def orchestrate_project(
    api_key: str,
    prompt: str,
) -> Dict:

    logger.info("Starting orchestration pipeline")

    architecture = await run_agent(api_key, "architect", prompt)

    frontend = await run_agent(api_key, "frontend", prompt, architecture)

    backend = await run_agent(api_key, "backend", prompt, architecture)

    security = await run_agent(
        api_key,
        "security",
        prompt,
        frontend + "\n\n" + backend,
    )

    tests = await run_agent(api_key, "qa", prompt, backend)

    devops = await run_agent(api_key, "devops", prompt, backend)

    return {
        "architecture": architecture,
        "frontend": frontend,
        "backend": backend,
        "security": security,
        "tests": tests,
        "devops": devops,
    }


# ---------------------------------------------------
# Streaming Orchestration
# ---------------------------------------------------
async def stream_orchestration(
    project_id: str,
    prompt: str,
    api_key: str,
) -> AsyncGenerator[str, None]:

    logger.info(f"Streaming orchestration started for {project_id}")

    yield f"data: Starting orchestration for {project_id}\n\n"

    agents = [
        "architect",
        "frontend",
        "backend",
        "security",
        "qa",
        "devops",
    ]

    context = ""

    for agent in agents:

        yield f"data: Running {agent} agent...\n\n"

        try:

            result = await run_agent(
                api_key=api_key,
                agent=agent,
                user_prompt=prompt,
                context=context,
            )

            context += "\n\n" + result[:2000]

            yield f"data: {agent} completed\n\n"
            yield f"data: {result}\n\n"

        except Exception as e:

            logger.error(f"{agent} failed: {e}")
            yield f"data: {agent} failed\n\n"

        await asyncio.sleep(0.5)

    yield "data: [COMPLETE] Project generated\n\n"
