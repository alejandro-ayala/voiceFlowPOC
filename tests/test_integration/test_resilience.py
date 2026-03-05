"""Tests for resilience primitives: circuit breaker, rate limiter, budget tracker."""

import time

import pytest

from integration.external_apis.resilience import (
    BudgetTracker,
    CircuitBreaker,
    CircuitState,
    ResilienceManager,
    TokenBucketRateLimiter,
)
from shared.exceptions.exceptions import (
    BudgetExceededException,
    CircuitBreakerOpenException,
    RateLimitExceededException,
)

# ---- CircuitBreaker ----


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(threshold=3)
        assert cb.get_state("svc") == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.OPEN

    def test_check_raises_when_open(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure("svc")
        cb.record_failure("svc")
        with pytest.raises(CircuitBreakerOpenException):
            cb.check("svc")

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure("svc")
        cb.record_success("svc")
        assert cb.get_state("svc") == CircuitState.CLOSED

    def test_half_open_after_recovery(self):
        cb = CircuitBreaker(threshold=1, recovery_seconds=0)
        cb.record_failure("svc")
        # With recovery_seconds=0 the first get_state sees OPEN then
        # immediately transitions to HALF_OPEN on elapsed >= 0
        state = cb.get_state("svc")
        assert state in (CircuitState.OPEN, CircuitState.HALF_OPEN)
        # Second call should definitely be HALF_OPEN
        time.sleep(0.01)
        assert cb.get_state("svc") == CircuitState.HALF_OPEN

    def test_independent_services(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure("a")
        cb.record_failure("a")
        assert cb.get_state("a") == CircuitState.OPEN
        assert cb.get_state("b") == CircuitState.CLOSED


# ---- TokenBucketRateLimiter ----


class TestTokenBucketRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_burst_up_to_rps(self):
        limiter = TokenBucketRateLimiter(rps=5)
        for _ in range(5):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_raises_when_exhausted(self):
        limiter = TokenBucketRateLimiter(rps=1)
        await limiter.acquire()
        with pytest.raises(RateLimitExceededException):
            await limiter.acquire()


# ---- BudgetTracker ----


class TestBudgetTracker:
    def test_allows_within_budget(self):
        bt = BudgetTracker(max_per_hour=1.0)
        bt.check_and_record("google_places_search")  # 0.032
        assert bt.get_current_spend() > 0

    def test_raises_when_over_budget(self):
        bt = BudgetTracker(max_per_hour=0.01)
        with pytest.raises(BudgetExceededException):
            for _ in range(100):
                bt.check_and_record("google_places_search")

    def test_free_operations_dont_count(self):
        bt = BudgetTracker(max_per_hour=0.001)
        bt.check_and_record("overpass_query")  # cost = 0.0
        assert bt.get_current_spend() == 0.0


# ---- ResilienceManager ----


class TestResilienceManager:
    @pytest.mark.asyncio
    async def test_pre_request_passes_when_healthy(self):
        rm = ResilienceManager(cb_threshold=5, rps=10, budget_per_hour=10.0)
        await rm.pre_request("svc", "overpass_query")

    @pytest.mark.asyncio
    async def test_pre_request_fails_on_open_circuit(self):
        rm = ResilienceManager(cb_threshold=1, rps=10, budget_per_hour=10.0)
        rm.record_failure("svc")
        with pytest.raises(CircuitBreakerOpenException):
            await rm.pre_request("svc", "overpass_query")
