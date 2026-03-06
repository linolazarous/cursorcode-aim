# backend/ai_queue.py

import asyncio
from logs import logger


class AIQueue:

    def __init__(self):
        self.queue = asyncio.Queue()

    async def add_task(self, task: dict):
        """
        Add AI job to queue
        """
        await self.queue.put(task)
        logger.info("Task added to AI queue")


    async def worker(self, handler):
        """
        Background worker
        """
        while True:
            task = await self.queue.get()

            try:
                await handler(task)
            except Exception as e:
                logger.error(f"Queue task error: {str(e)}")

            self.queue.task_done()


    async def start_workers(self, handler, workers: int = 3):
        """
        Start background workers
        """

        for _ in range(workers):
            asyncio.create_task(self.worker(handler))

        logger.info(f"{workers} AI queue workers started")
