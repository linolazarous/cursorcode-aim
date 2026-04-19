"""
CursorCode AI - Feedback Collector
Collects user feedback on AI-generated code for continuous improvement.
Stores in MongoDB for analysis.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List

from core.database import db

logger = logging.getLogger("feedback_collector")


async def submit_feedback(
    user_id: str,
    project_id: str,
    rating: int,
    feedback_type: str = "general",
    comment: str = "",
    agent: Optional[str] = None,
    file_name: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """Store user feedback on AI output."""
    if rating < 1 or rating > 5:
        return {"error": "Rating must be between 1 and 5"}

    feedback = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "project_id": project_id,
        "rating": rating,
        "type": feedback_type,
        "comment": comment,
        "agent": agent,
        "file_name": file_name,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.ai_feedback.insert_one(feedback)
    logger.info(f"Feedback collected: user={user_id}, rating={rating}, type={feedback_type}")

    return {"id": feedback["id"], "message": "Feedback submitted"}


async def get_feedback_stats(project_id: Optional[str] = None) -> Dict:
    """Get aggregated feedback statistics."""
    query = {}
    if project_id:
        query["project_id"] = project_id

    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"},
            "count_1": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
            "count_2": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}},
            "count_3": {"$sum": {"$cond": [{"$eq": ["$rating", 3]}, 1, 0]}},
            "count_4": {"$sum": {"$cond": [{"$eq": ["$rating", 4]}, 1, 0]}},
            "count_5": {"$sum": {"$cond": [{"$eq": ["$rating", 5]}, 1, 0]}},
        }},
    ]

    results = await db.ai_feedback.aggregate(pipeline).to_list(1)
    if not results:
        return {"total": 0, "avg_rating": 0, "distribution": {}}

    r = results[0]
    return {
        "total": r["total"],
        "avg_rating": round(r["avg_rating"], 2),
        "distribution": {
            "1": r["count_1"], "2": r["count_2"], "3": r["count_3"],
            "4": r["count_4"], "5": r["count_5"],
        },
    }


async def get_recent_feedback(
    project_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict]:
    """Get recent feedback entries."""
    query = {}
    if project_id:
        query["project_id"] = project_id

    feedback = await db.ai_feedback.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)

    return feedback
