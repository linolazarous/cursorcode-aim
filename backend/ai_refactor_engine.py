"""CursorCode AI - AI Refactor Engine"""
import logging
from ai_agents import run_agent
from ai_security import AISecurity

logger = logging.getLogger("ai_refactor_engine")

class AIRefactorEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def refactor_code(self, code: str) -> str:
        try:
            safe_code = AISecurity.sanitize_code(code)
            prompt = f"Refactor for clarity, performance, best practices:\n{safe_code}"
            return await run_agent(self.api_key, "backend", prompt)
        except Exception as e:
            logger.error(f"Refactor failed: {e}")
            return code
