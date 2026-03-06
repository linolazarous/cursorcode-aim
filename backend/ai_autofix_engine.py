# backend/ai_autofix_engine.py

import logging
from ai_agents import run_agent
from ai_security import AISecurity

logger = logging.getLogger("ai_autofix_engine")

class AIAutoFixEngine:

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def fix_code(self, code: str) -> str:
        safe_code = AISecurity.sanitize_code(code)
        prompt = f"Fix bugs and optimize the following code:\n{safe_code}"

        result = await run_agent(self.api_key, "backend", prompt)
        return result
