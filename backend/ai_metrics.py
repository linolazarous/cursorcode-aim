# backend/ai_metrics.py

import time
from collections import defaultdict


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
        avg_time = 0

        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)

        return {
            "requests": self.metrics["requests"],
            "errors": self.metrics["errors"],
            "avg_response_time": avg_time,
        }
