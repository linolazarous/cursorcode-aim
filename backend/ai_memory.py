"""
CursorCode AI - AI Memory System
Stores prompts, architectures, generated code, agent outputs.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict
from pymongo import MongoClient, errors

logger = logging.getLogger("ai_memory")

class AIMemory:
    def __init__(self, mongo_url: str, db_name: str):
        try:
            self.client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            self.db = self.client[db_name]
            self.memory_collection = self.db["ai_memory"]
            self.client.admin.command("ping")
            logger.info(f"AI Memory connected to MongoDB")
        except errors.PyMongoError as e:
            logger.exception(f"MongoDB connection failed: {e}")
            raise

    def store_memory(self, user_email: str, prompt: str, architecture: str, frontend: str, backend: str):
        try:
            record = {
                "user": user_email, "prompt": prompt, "architecture": architecture,
                "frontend": frontend, "backend": backend,
                "created": datetime.now(timezone.utc),
            }
            self.memory_collection.insert_one(record)
            logger.info(f"Stored AI memory for {user_email}")
        except errors.PyMongoError as e:
            logger.exception(f"Failed to store AI memory: {e}")

    def search_memory(self, user_email: str, limit: int = 5) -> List[Dict]:
        try:
            cursor = self.memory_collection.find({"user": user_email}).sort("created", -1).limit(limit)
            return [
                {"prompt": doc.get("prompt", ""), "architecture": doc.get("architecture", ""),
                 "frontend": doc.get("frontend", ""), "backend": doc.get("backend", "")}
                for doc in cursor
            ]
        except errors.PyMongoError as e:
            logger.exception(f"Failed to search AI memory: {e}")
            return []

    def build_context(self, user_email: str) -> str:
        memories = self.search_memory(user_email)
        if not memories:
            return ""
        context = "Previous projects:\n\n"
        for m in memories:
            context += f"Prompt:\n{m['prompt'][:500]}\n\nArchitecture:\n{m['architecture'][:800]}\n\n"
        return context.strip()
