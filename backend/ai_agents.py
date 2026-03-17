"""
CursorCode AI - Multi-Agent Engineering System
Agents: Architect, Frontend, Backend, Security, QA, DevOps
"""

import asyncio
import logging
from typing import Dict, List
import httpx

logger = logging.getLogger("ai_agents")

XAI_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = "grok-2-latest"

async def call_grok(
    api_key: str,
    messages: List[Dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 4096,
):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            XAI_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]

AGENT_PROMPTS = {
    "architect": """You are a senior software architect. Design a scalable production architecture.
Include: system components, services, database schema, infrastructure, security considerations.""",
    "frontend": """You are a senior frontend engineer. Generate modern UI using React + TailwindCSS.
Requirements: reusable components, responsive layout, clean project structure.""",
    "backend": """You are a senior backend engineer. Generate a production backend using FastAPI or Node.js.
Include: authentication, database models, REST APIs, validation, error handling.""",
    "security": """You are a cybersecurity auditor. Review the generated system.
Find: vulnerabilities, injection risks, insecure configs, auth issues. Provide fixes.""",
    "qa": """You are a QA automation engineer. Generate unit tests, integration tests, API tests using modern frameworks.""",
    "devops": """You are a DevOps engineer. Generate: Dockerfile, docker-compose, CI/CD pipeline, production deployment steps.""",
}

async def run_agent(api_key: str, agent: str, prompt: str, context: str = "", model: str = DEFAULT_MODEL):
    if agent not in AGENT_PROMPTS:
        raise ValueError(f"Unknown agent: {agent}")
    messages = [
        {"role": "system", "content": AGENT_PROMPTS[agent]},
        {"role": "user", "content": f"User Request:\n{prompt}\n\nContext:\n{context}"},
    ]
    return await call_grok(api_key=api_key, model=model, messages=messages)

async def generate_full_project(api_key: str, prompt: str, model: str = DEFAULT_MODEL):
    logger.info("Starting AI multi-agent generation")
    architecture = await run_agent(api_key, "architect", prompt, "", model)
    frontend = await run_agent(api_key, "frontend", prompt, architecture, model)
    backend = await run_agent(api_key, "backend", prompt, architecture, model)
    security = await run_agent(api_key, "security", prompt, frontend + backend, model)
    tests = await run_agent(api_key, "qa", prompt, backend, model)
    devops = await run_agent(api_key, "devops", prompt, backend, model)
    return {
        "architecture": architecture, "frontend": frontend, "backend": backend,
        "security": security, "tests": tests, "devops": devops,
    }

async def generate_parallel_project(api_key: str, prompt: str, model: str = DEFAULT_MODEL):
    architecture = await run_agent(api_key, "architect", prompt, "", model)
    tasks = [
        run_agent(api_key, "frontend", prompt, architecture, model),
        run_agent(api_key, "backend", prompt, architecture, model),
    ]
    frontend, backend = await asyncio.gather(*tasks)
    security = await run_agent(api_key, "security", prompt, frontend + backend, model)
    tests = await run_agent(api_key, "qa", prompt, backend, model)
    devops = await run_agent(api_key, "devops", prompt, backend, model)
    return {
        "architecture": architecture, "frontend": frontend, "backend": backend,
        "security": security, "tests": tests, "devops": devops,
    }
