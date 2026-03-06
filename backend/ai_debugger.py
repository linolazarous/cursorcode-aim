# backend/ai_debugger.py

import logging
from ai_agents import run_agent
from ai_security import AISecurity

logger = logging.getLogger("ai_debugger")

class AIDebugger:

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def debug_code(self, code: str) -> str:
        safe_code = AISecurity.sanitize_code(code)
        prompt = f"Debug this code and explain any errors:\n{safe_code}"
        result = await run_agent(self.api_key, "backend", prompt)
        return result
