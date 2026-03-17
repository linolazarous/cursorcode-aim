"""
CursorCode AI - AI Metrics Tracking
"""

import time
from collections import defaultdict
import logging

logger = logging.getLogger("ai_metrics")

class AIMetrics:
    def __init__(self):
        self.metrics = defaultdict(int)
        self.response_times = []

    def track_request(self):
        self.metrics["requests"] += 1

    def track_error(self):
        self.metrics["errors"] += 1

    def track_response_time(self, start_time):
        duration = time.time() - start_time
        self.response_times.append(duration)

    def get_metrics(self):
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            "requests": self.metrics["requests"],
            "errors": self.metrics["errors"],
            "avg_response_time": round(avg_time, 3),
        }

_global_metrics = AIMetrics()

def track_ai_usage(user_email: str):
    try:
        _global_metrics.track_request()
    except Exception as e:
        logger.error(f"Failed to track AI usage: {e}")

def get_platform_stats() -> dict:
    try:
        return _global_metrics.get_metrics()
    except Exception:
        return {"requests": 0, "errors": 0, "avg_response_time": 0}

def save_event(event: str, user_email: str):
    logger.info(f"Event tracked: {event} for {user_email}")
    _global_metrics.track_request()
