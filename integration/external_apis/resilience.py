"""Resilience primitives for external API calls: circuit breaker, rate limiter, budget tracker."""

import asyncio
import time
from enum import Enum

import structlog

from shared.exceptions.exceptions import (
    BudgetExceededException,
    CircuitBreakerOpenException,
    RateLimitExceededException,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Tracks consecutive failures per service and opens circuit when threshold is reached."""

    def __init__(self, threshold: int = 5, recovery_seconds: int = 60):
        self._threshold = threshold
        self._recovery_seconds = recovery_seconds
        self._failures: dict[str, int] = {}
        self._last_failure: dict[str, float] = {}
        self._state: dict[str, CircuitState] = {}

    def get_state(self, service: str) -> CircuitState:
        state = self._state.get(service, CircuitState.CLOSED)
        if state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure.get(service, 0)
            if elapsed >= self._recovery_seconds:
                self._state[service] = CircuitState.HALF_OPEN
                return CircuitState.HALF_OPEN
        return state

    def check(self, service: str) -> None:
        if self.get_state(service) == CircuitState.OPEN:
            raise CircuitBreakerOpenException(
                f"Circuit breaker open for {service}",
                error_code="CIRCUIT_OPEN",
            )

    def record_success(self, service: str) -> None:
        self._failures[service] = 0
        self._state[service] = CircuitState.CLOSED

    def record_failure(self, service: str) -> None:
        self._failures[service] = self._failures.get(service, 0) + 1
        self._last_failure[service] = time.monotonic()
        if self._failures[service] >= self._threshold:
            self._state[service] = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                service=service,
                failures=self._failures[service],
            )


# ---------------------------------------------------------------------------
# Token Bucket Rate Limiter
# ---------------------------------------------------------------------------


class TokenBucketRateLimiter:
    """Async-safe token bucket rate limiter."""

    def __init__(self, rps: int = 10):
        self._rps = max(rps, 1)
        self._tokens = float(self._rps)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._rps, self._tokens + elapsed * self._rps)
            self._last_refill = now
            if self._tokens < 1.0:
                raise RateLimitExceededException(
                    "Rate limit exceeded — try again shortly",
                    error_code="RATE_LIMITED",
                )
            self._tokens -= 1.0


# ---------------------------------------------------------------------------
# Budget Tracker
# ---------------------------------------------------------------------------


class BudgetTracker:
    """Tracks estimated API cost within a rolling 1-hour window."""

    COST_ESTIMATES: dict[str, float] = {
        "google_places_search": 0.032,
        "google_places_details": 0.017,
        "google_directions": 0.010,
        "openroute_directions": 0.0,
        "overpass_query": 0.0,
    }

    def __init__(self, max_per_hour: float = 1.0):
        self._max_per_hour = max_per_hour
        self._costs: list[tuple[float, float]] = []

    def _current_total(self) -> float:
        now = time.monotonic()
        cutoff = now - 3600
        self._costs = [(t, c) for t, c in self._costs if t > cutoff]
        return sum(c for _, c in self._costs)

    def check_and_record(self, operation: str) -> None:
        cost = self.COST_ESTIMATES.get(operation, 0.01)
        current = self._current_total()
        if current + cost > self._max_per_hour:
            raise BudgetExceededException(
                f"API budget exceeded: ${current:.3f}/${self._max_per_hour:.2f} per hour",
                error_code="BUDGET_EXCEEDED",
            )
        self._costs.append((time.monotonic(), cost))

    def get_current_spend(self) -> float:
        return self._current_total()


# ---------------------------------------------------------------------------
# Resilience Manager (facade)
# ---------------------------------------------------------------------------


class ResilienceManager:
    """Combines circuit breaker, rate limiter, and budget tracker into a single facade."""

    def __init__(
        self,
        cb_threshold: int = 5,
        cb_recovery: int = 60,
        rps: int = 10,
        budget_per_hour: float = 1.0,
    ):
        self.circuit_breaker = CircuitBreaker(cb_threshold, cb_recovery)
        self.rate_limiter = TokenBucketRateLimiter(rps)
        self.budget_tracker = BudgetTracker(budget_per_hour)

    async def pre_request(self, service: str, operation: str) -> None:
        """Check all resilience gates before making an API call."""
        self.circuit_breaker.check(service)
        await self.rate_limiter.acquire()
        self.budget_tracker.check_and_record(operation)

    def record_success(self, service: str) -> None:
        self.circuit_breaker.record_success(service)

    def record_failure(self, service: str) -> None:
        self.circuit_breaker.record_failure(service)
