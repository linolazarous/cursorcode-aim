"""
CursorCode AI - AI Streaming
Stream Grok/xAI agent responses
"""

import asyncio
from typing import AsyncGenerator
from backend.orchestrator import run_agent
from backend.utils import truncate_text

async def stream_ai_response(api_key: str, agent: str, prompt: str) -> AsyncGenerator[str, None]:
    yield f"data: Starting {agent} agent...\n\n"

    context = ""
    result = await run_agent(api_key, agent, prompt, context)
    context += truncate_text(result)

    yield f"data: {result}\n\n"
    yield f"data: [COMPLETE] {agent} finished\n\n"

    await asyncio.sleep(1)
