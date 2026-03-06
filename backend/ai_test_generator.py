# backend/ai_test_generator.py

import logging
from ai_agents import run_agent

logger = logging.getLogger("ai_test_generator")

class AITestGenerator:

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate_tests(self, code: str) -> str:
        prompt = f"Generate unit and integration tests for the following code:\n{code}"
        result = await run_agent(self.api_key, "qa", prompt)
        return result
