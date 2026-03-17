"""CursorCode AI - AI Project Architect"""
import logging
import json
from ai_agents import run_agent

logger = logging.getLogger("ai_project_architect")

class AIProjectArchitect:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def design_architecture(self, project_prompt: str) -> dict:
        prompt = f"Design full production-ready architecture for:\n{project_prompt}"
        try:
            result = await run_agent(self.api_key, "architect", prompt)
            try:
                return {"architecture": json.loads(result)}
            except json.JSONDecodeError:
                return {"architecture": result}
        except Exception as e:
            logger.error(f"Architecture generation failed: {e}")
            return {"architecture": None, "error": str(e)}
