import math
from collections import deque
from threading import Lock
from time import monotonic


class SlidingWindowRateLimiter:
    """Single-process local limit; distributed deployments need a shared store."""

    def __init__(self):
        self.clients = {}
        self.global_requests = deque()
        self.lock = Lock()

    def check(self, key, now=None):
        now = monotonic() if now is None else now
        with self.lock:
            for client, times in list(self.clients.items()):
                while times and times[0] <= now - 60:
                    times.popleft()
                if not times:
                    del self.clients[client]
            while self.global_requests and self.global_requests[0] <= now - 60:
                self.global_requests.popleft()
            if len(self.global_requests) >= 60:
                return max(1, math.ceil(60 - (now - self.global_requests[0])))
            times = self.clients.setdefault(key, deque())
            if len(times) >= 10:
                return max(1, math.ceil(60 - (now - times[0])))
            times.append(now)
            self.global_requests.append(now)
            return 0
