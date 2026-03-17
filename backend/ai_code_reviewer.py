"""CursorCode AI - AI Code Reviewer"""
import logging
from ai_agents import run_agent
from ai_security import AISecurity

logger = logging.getLogger("ai_code_reviewer")

class AICodeReviewer:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def review_code(self, code: str) -> str:
        try:
            if not AISecurity.validate_prompt(code):
                return "Code contains unsafe patterns."
            prompt = f"Review for security, performance, best practices:\n{code}"
            return await run_agent(self.api_key, "security", prompt, context="")
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return "Code review failed."
