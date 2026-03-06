# backend/ai_code_reviewer.py

import logging
from ai_security import AISecurity
from ai_agents import run_agent  # reuse your agent executor

logger = logging.getLogger("ai_code_reviewer")

class AICodeReviewer:

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def review_code(self, code: str) -> str:
        if not AISecurity.validate_prompt(code):
            return "Code contains unsafe patterns."

        prompt = f"Review this code for best practices and security:\n{code}"

        result = await run_agent(self.api_key, "security", prompt, context="")
        return result
