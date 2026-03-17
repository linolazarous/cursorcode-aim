"""
CursorCode AI - AI Streaming
Stream Grok/xAI agent responses with SSE-compatible output.
"""

import os
import asyncio
import logging
from typing import AsyncGenerator

from ai_agents import run_agent
from utils import truncate_text

logger = logging.getLogger("ai_streaming")

async def stream_ai_response(api_key: str, agent: str, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
    try:
        yield f"data: [INFO] Starting {agent} agent...\n\n"
        result = await run_agent(api_key, agent, prompt, context)
        truncated = truncate_text(result, max_length=2000)
        for line in truncated.splitlines():
            yield f"data: {line}\n\n"
            await asyncio.sleep(0.01)
        yield f"data: [COMPLETE] {agent} finished\n\n"
    except Exception as e:
        logger.exception(f"Error in {agent} streaming")
        yield f"data: [ERROR] {agent} failed: {str(e)}\n\n"

async def stream_project_build(prompt: str, user_email: str):
    from fastapi.responses import StreamingResponse
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("XAI_API_KEY not set")
    agents = ["architect", "frontend", "backend", "security", "qa", "devops"]
    context = ""

    async def event_generator():
        nonlocal context
        for agent in agents:
            async for chunk in stream_ai_response(api_key, agent, prompt, context):
                if chunk.startswith("data: "):
                    context += chunk[6:]
                yield chunk
            await asyncio.sleep(0.05)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
