"""
CursorCode AI
AI Memory System

Stores:
- prompts
- architectures
- generated code
- agent outputs

Allows retrieval of past knowledge for new prompts.
"""

import logging
from datetime import datetime
from typing import List, Dict

from pymongo import MongoClient

logger = logging.getLogger("ai_memory")


class AIMemory:

    def __init__(self, mongo_url: str, db_name: str):

        self.client = MongoClient(mongo_url)
        self.db = self.client[db_name]

        self.memory_collection = self.db["ai_memory"]

    # =====================================================
    # STORE MEMORY
    # =====================================================

    def store_memory(
        self,
        user_email: str,
        prompt: str,
        architecture: str,
        frontend: str,
        backend: str,
    ):

        record = {

            "user": user_email,
            "prompt": prompt,

            "architecture": architecture,
            "frontend": frontend,
            "backend": backend,

            "created": datetime.utcnow(),
        }

        self.memory_collection.insert_one(record)

        logger.info("AI memory stored")

    # =====================================================
    # SEARCH MEMORY
    # =====================================================

    def search_memory(self, user_email: str, limit: int = 5) -> List[Dict]:

        cursor = self.memory_collection.find(
            {"user": user_email}
        ).sort("created", -1).limit(limit)

        results = []

        for doc in cursor:

            results.append({
                "prompt": doc.get("prompt"),
                "architecture": doc.get("architecture"),
                "frontend": doc.get("frontend"),
                "backend": doc.get("backend"),
            })

        return results

    # =====================================================
    # BUILD CONTEXT STRING
    # =====================================================

    def build_context(self, user_email: str) -> str:

        memories = self.search_memory(user_email)

        if not memories:
            return ""

        context = "Previous projects:\n\n"

        for m in memories:

            context += f"""
Prompt:
{m['prompt']}

Architecture:
{m['architecture'][:800]}

"""

        return context
