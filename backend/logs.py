"""
CursorCode AI - Logging Service
Centralized logging for AI operations, payments, and system events
"""

import logging
from backend.db_models import AI_Logs
from datetime import datetime

logger = logging.getLogger("cursorcode_ai")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_event(event_type: str, message: str, extra: dict = None):
    """Logs an event to console and MongoDB"""
    log_message = f"{event_type}: {message}"
    logger.info(log_message)

    doc = {
        "type": event_type,
        "message": message,
        "extra": extra or {},
        "timestamp": datetime.utcnow()
    }
    AI_Logs.insert_one(doc)
