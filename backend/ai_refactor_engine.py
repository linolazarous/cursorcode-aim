# backend/ai_refactor_engine.py

import logging
from ai_agents import run_agent

logger = logging.getLogger("ai_refactor_engine")

class AIRefactorEngine:

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def refactor_code(self, code: str) -> str:
        prompt = f"Refactor this code for clarity, performance, and best practices:\n{code}"
        result = await run_agent(self.api_key, "backend", prompt)
        return result
