"""CursorCode AI - AI Debugger"""
import logging
from ai_agents import run_agent
from ai_security import AISecurity

logger = logging.getLogger("ai_debugger")

class AIDebugger:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def debug_code(self, code: str) -> str:
        try:
            safe_code = AISecurity.sanitize_code(code)
            prompt = f"Debug and explain issues:\n{safe_code}"
            return await run_agent(self.api_key, "backend", prompt)
        except Exception as e:
            logger.error(f"Debugging failed: {e}")
            return "Debugging failed."
