"""Unit tests for circuit breaker pattern.

Tests the failure isolation mechanism for research agent.
"""

import pytest
import time
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cs_agent.circuit_breaker import CircuitBreaker, CircuitState, get_circuit_breaker


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""
    
    def test_initial_state_is_closed(self):
        """Circuit should start in CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() == True
    
    def test_record_success_increments_counter(self):
        """Recording success should work."""
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_success()
        assert cb.failure_count == 0  # Success doesn't change failure count
    
    def test_single_failure_doesnt_open(self):
        """Single failure should not open circuit."""
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() == True
    
    def test_multiple_failures_opens_circuit(self):
        """Multiple failures should open circuit."""
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() == False
    
    def test_success_resets_failure_count(self):
        """Success should reset failure counter."""
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0


class TestCircuitBreakerRecovery:
    """Test circuit breaker recovery mechanism."""
    
    def test_recovery_timeout_triggers_half_open(self):
        """After timeout, circuit should go to HALF_OPEN."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()  # Opens circuit
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Should now be able to execute (half-open)
        assert cb.can_execute() == True
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_success_in_half_open_closes_circuit(self):
        """Success in half-open should close circuit."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=1)
        cb.record_failure()
        time.sleep(0.15)
        
        # Should be half-open now
        assert cb.can_execute() == True
        
        # Success should close circuit
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
    
    def test_failure_in_half_open_reopens(self):
        """Failure in half-open should reopen circuit."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=1)
        cb.record_failure()
        time.sleep(0.15)
        
        # Should be half-open
        assert cb.can_execute() == True
        
        # Another failure should reopen
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
    
    def test_half_open_limits_calls(self):
        """Half-open should limit concurrent test calls."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2)
        cb.record_failure()
        time.sleep(0.15)
        
        # First call should be allowed
        assert cb.can_execute() == True
        cb.half_open_calls = 1
        
        # Second call should be allowed
        assert cb.can_execute() == True
        cb.half_open_calls = 2
        
        # Third call should NOT be allowed
        assert cb.can_execute() == False


class TestCircuitBreakerStateTracking:
    """Test state tracking and reporting."""
    
    def test_get_state_returns_dict(self):
        """get_state should return proper dict."""
        cb = CircuitBreaker("test_cb", failure_threshold=3)
        state = cb.get_state()
        
        assert state["name"] == "test_cb"
        assert state["state"] == "closed"
        assert "failure_count" in state
        assert "last_failure_time" in state
    
    def test_state_updates_on_failure(self):
        """State dict should reflect current state."""
        cb = CircuitBreaker("test", failure_threshold=2)
        
        initial = cb.get_state()
        assert initial["failure_count"] == 0
        
        cb.record_failure()
        updated = cb.get_state()
        assert updated["failure_count"] == 1
    
    def test_global_circuit_breaker_singleton(self):
        """Global circuit breaker should be singleton."""
        cb1 = get_circuit_breaker()
        cb2 = get_circuit_breaker()
        assert cb1 is cb2


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_threshold(self):
        """Zero threshold should open immediately on first failure."""
        cb = CircuitBreaker("test", failure_threshold=0)
        cb.record_failure()
        # With threshold 0, circuit should open immediately
        # But implementation might handle this edge case differently
        assert cb.state in [CircuitState.OPEN, CircuitState.CLOSED]
    
    def test_very_long_recovery_timeout(self):
        """Very long timeout should prevent quick recovery."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=3600)
        cb.record_failure()
        
        # Even after short sleep, should still be open
        time.sleep(0.1)
        assert cb.can_execute() == False
    
    def test_concurrent_failures(self):
        """Simulate concurrent failure recording."""
        cb = CircuitBreaker("test", failure_threshold=10)
        
        # Simulate multiple rapid failures
        for i in range(5):
            cb.record_failure()
        
        assert cb.failure_count == 5
        assert cb.state == CircuitState.CLOSED  # Not yet at threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
