# backend/ai_project_architect.py

import logging
from ai_agents import run_agent

logger = logging.getLogger("ai_project_architect")

class AIProjectArchitect:

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def design_architecture(self, project_prompt: str) -> str:
        prompt = f"Design full production-ready architecture for:\n{project_prompt}"

        result = await run_agent(self.api_key, "architect", prompt)
        return result
