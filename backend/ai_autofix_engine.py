"""CursorCode AI - AI Auto-Fix Engine"""
import logging
from ai_agents import run_agent
from ai_security import AISecurity

logger = logging.getLogger("ai_autofix_engine")

class AIAutoFixEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fix_code(self, code: str) -> str:
        try:
            safe_code = AISecurity.sanitize_code(code)
            prompt = f"Fix bugs, improve performance, and optimize:\n{safe_code}"
            return await run_agent(self.api_key, "backend", prompt)
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
            return code
