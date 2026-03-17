"""
CursorCode AI - Rate Limiter
Plan-based rate limiting per user.
"""

import time
import logging
from collections import defaultdict

logger = logging.getLogger("ai_rate_limiter")

PLAN_LIMITS = {
    "starter": 20,
    "standard": 60,
    "pro": 120,
    "premier": 300,
    "ultra": 1000,
}

class AIRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)

    def allow_request(self, user_id: str, plan: str = "starter") -> bool:
        now = time.time()
        window_start = now - 60
        self.requests[user_id] = [t for t in self.requests[user_id] if t > window_start]
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])
        if len(self.requests[user_id]) >= limit:
            logger.warning(f"Rate limit exceeded for {user_id} (limit={limit})")
            return False
        self.requests[user_id].append(now)
        return True

_rate_limiter = AIRateLimiter()

def check_rate_limit(user_id: str, plan: str = "starter") -> bool:
    try:
        return _rate_limiter.allow_request(user_id, plan)
    except Exception:
        return True  # fail open
