# backend/ai_rate_limiter.py

import time
from collections import defaultdict


class AIRateLimiter:

    def __init__(self, limit_per_minute=60):
        self.limit = limit_per_minute
        self.requests = defaultdict(list)

    def allow_request(self, user_id: str) -> bool:
        """
        Check if user exceeded rate limit.
        """

        now = time.time()

        window = now - 60

        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > window
        ]

        if len(self.requests[user_id]) >= self.limit:
            return False

        self.requests[user_id].append(now)

        return True
