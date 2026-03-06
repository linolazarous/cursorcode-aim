# backend/ai_router.py

from ai_agents import AIAgentFactory
from logs import logger


class AIRouter:
    """
    Routes user AI requests to the correct AI agent.
    """

    def __init__(self):
        self.agent_factory = AIAgentFactory()

    async def route(self, task_type: str, payload: dict):
        """
        Route task to appropriate AI agent.
        """

        logger.info(f"Routing task: {task_type}")

        agent = self.agent_factory.get_agent(task_type)

        if not agent:
            raise ValueError(f"No agent found for task type: {task_type}")

        result = await agent.run(payload)

        return result
