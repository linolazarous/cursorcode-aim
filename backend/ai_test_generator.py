"""CursorCode AI - AI Test Generator"""
import logging
from ai_agents import run_agent

logger = logging.getLogger("ai_test_generator")

class AITestGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_tests(self, code: str) -> str:
        prompt = f"Generate unit and integration tests for:\n{code}"
        return await run_agent(self.api_key, "qa", prompt)
