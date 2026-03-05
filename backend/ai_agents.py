"""
CursorCode AI
AI Multi-Agent Engineering System

Agents:
- Architect
- Frontend Engineer
- Backend Engineer
- Security Auditor
- QA Engineer
- DevOps Engineer
"""

import asyncio
import logging
from typing import Dict, List

import httpx

logger = logging.getLogger("ai_agents")

XAI_URL = "https://api.x.ai/v1/chat/completions"


# =====================================================
# CORE GROK CALL
# =====================================================

async def call_grok(
    api_key: str,
    model: str,
    messages: List[Dict],
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


# =====================================================
# AGENT PROMPTS
# =====================================================

AGENT_SYSTEM_PROMPTS = {

    "architect":
        """
You are a senior software architect.

Design scalable production architecture.

Include:
- system components
- microservices
- database schema
- infrastructure
- security considerations
""",

    "frontend":
        """
You are a senior frontend engineer.

Generate modern UI code using:
React + TailwindCSS

Best practices:
- clean structure
- reusable components
- responsive layout
""",

    "backend":
        """
You are a senior backend engineer.

Generate production backend APIs.

Preferred stack:
FastAPI or Node.js

Include:
- authentication
- database models
- endpoints
- error handling
""",

    "security":
        """
You are a cybersecurity expert.

Audit the generated code.

Find:
- vulnerabilities
- auth weaknesses
- injection risks
- insecure configs

Provide fixes.
""",

    "qa":
        """
You are a QA automation engineer.

Generate:

- unit tests
- integration tests
- API tests

Use modern testing frameworks.
""",

    "devops":
        """
You are a DevOps engineer.

Generate deployment infrastructure:

Include:

- Dockerfile
- docker-compose
- CI/CD pipeline
- cloud deployment steps
"""
}


# =====================================================
# AGENT EXECUTION
# =====================================================

async def run_agent(
    api_key: str,
    model: str,
    agent: str,
    user_prompt: str,
    context: str = ""
):

    system_prompt = AGENT_SYSTEM_PROMPTS[agent]

    messages = [

        {
            "role": "system",
            "content": system_prompt
        },

        {
            "role": "user",
            "content": f"""
User request:

{user_prompt}

Existing context:

{context}
"""
        }
    ]

    result = await call_grok(
        api_key=api_key,
        model=model,
        messages=messages,
    )

    return result


# =====================================================
# FULL PROJECT GENERATION
# =====================================================

async def generate_full_project(
    api_key: str,
    model: str,
    prompt: str,
):

    logger.info("Starting AI multi-agent generation")

    architecture = await run_agent(
        api_key,
        model,
        "architect",
        prompt,
    )

    frontend = await run_agent(
        api_key,
        model,
        "frontend",
        prompt,
        architecture,
    )

    backend = await run_agent(
        api_key,
        model,
        "backend",
        prompt,
        architecture,
    )

    security = await run_agent(
        api_key,
        model,
        "security",
        prompt,
        frontend + backend,
    )

    tests = await run_agent(
        api_key,
        model,
        "qa",
        prompt,
        backend,
    )

    devops = await run_agent(
        api_key,
        model,
        "devops",
        prompt,
        backend,
    )

    return {

        "architecture": architecture,
        "frontend": frontend,
        "backend": backend,
        "security": security,
        "tests": tests,
        "devops": devops,
    }


# =====================================================
# PARALLEL AGENT EXECUTION
# =====================================================

async def generate_parallel_project(
    api_key: str,
    model: str,
    prompt: str
):

    architecture = await run_agent(
        api_key,
        model,
        "architect",
        prompt,
    )

    tasks = [

        run_agent(api_key, model, "frontend", prompt, architecture),

        run_agent(api_key, model, "backend", prompt, architecture),
    ]

    frontend, backend = await asyncio.gather(*tasks)

    security = await run_agent(
        api_key,
        model,
        "security",
        prompt,
        frontend + backend,
    )

    tests = await run_agent(
        api_key,
        model,
        "qa",
        prompt,
        backend,
    )

    devops = await run_agent(
        api_key,
        model,
        "devops",
        prompt,
        backend,
    )

    return {

        "architecture": architecture,
        "frontend": frontend,
        "backend": backend,
        "security": security,
        "tests": tests,
        "devops": devops,
    }


# =====================================================
# STREAMING AGENT EXECUTION
# =====================================================

async def stream_project_generation(
    api_key: str,
    model: str,
    prompt: str
):

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

        yield f"Running {agent} agent..."

        result = await run_agent(
            api_key,
            model,
            agent,
            prompt,
            context,
        )

        context += "\n\n" + result[:2000]

        yield f"{agent} completed"

        await asyncio.sleep(1)

    yield "AI generation complete"
