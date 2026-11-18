"""Thread-safe sliding-window login rate limiter (per IP and per username)."""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict

from app.core.errors import RateLimitExceededError


class LoginRateLimiter:
    """In-process sliding-window limiter guarding `/auth/login` against brute-force attacks."""

    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._ip_failures: dict[str, list[float]] = defaultdict(list)
        self._user_failures: dict[str, list[float]] = defaultdict(list)

    def _prune(self, bucket: list[float], now: float) -> list[float]:
        cutoff = now - self.window_seconds
        return [ts for ts in bucket if ts > cutoff]

    def check_allowed(self, *, client_ip: str, username: str) -> None:
        now = time.monotonic()
        ip_key = (client_ip or "unknown").strip().lower()
        user_key = (username or "").strip().lower()

        with self._lock:
            ip_hits = self._prune(self._ip_failures[ip_key], now)
            self._ip_failures[ip_key] = ip_hits

            user_hits: list[float] = []
            if user_key:
                user_hits = self._prune(self._user_failures[user_key], now)
                self._user_failures[user_key] = user_hits

            blocking_bucket: list[float] | None = None
            if len(ip_hits) >= self.max_attempts:
                blocking_bucket = ip_hits
            elif user_key and len(user_hits) >= self.max_attempts:
                blocking_bucket = user_hits

            if blocking_bucket is not None:
                oldest = min(blocking_bucket)
                retry_after = max(1, math.ceil(self.window_seconds - (now - oldest)))
                raise RateLimitExceededError(
                    headers={"Retry-After": str(retry_after)},
                )

    def record_failure(self, *, client_ip: str, username: str) -> None:
        now = time.monotonic()
        ip_key = (client_ip or "unknown").strip().lower()
        user_key = (username or "").strip().lower()

        with self._lock:
            ip_hits = self._prune(self._ip_failures[ip_key], now)
            ip_hits.append(now)
            self._ip_failures[ip_key] = ip_hits

            if user_key:
                user_hits = self._prune(self._user_failures[user_key], now)
                user_hits.append(now)
                self._user_failures[user_key] = user_hits

    def reset_account_window(self, *, username: str) -> None:
        user_key = (username or "").strip().lower()
        if not user_key:
            return
        with self._lock:
            self._user_failures.pop(user_key, None)

    def clear_all(self) -> None:
        with self._lock:
            self._ip_failures.clear()
            self._user_failures.clear()
