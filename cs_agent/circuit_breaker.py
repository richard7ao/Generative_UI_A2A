"""Circuit breaker pattern for research agent to prevent cascading failures.

Based on patterns from: https://github.com/maeste/multi-agent-a2a
Prevents research agent timeouts from blocking the entire CS agent.
"""

import time
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker for research agent calls.
    
    Prevents timeout cascading failures by:
    1. Tracking failure rates
    2. Opening circuit after threshold failures
    3. Periodically testing recovery
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                print(f"[CircuitBreaker:{self.name}] Entering HALF_OPEN state")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                # Recovery successful, close circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                print(f"[CircuitBreaker:{self.name}] Circuit CLOSED (recovered)")
        else:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
                print(f"[CircuitBreaker:{self.name}] Failure count reset")
    
    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Recovery failed, reopen circuit
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            print(f"[CircuitBreaker:{self.name}] Circuit OPEN (recovery failed)")
        elif self.state == CircuitState.CLOSED and \
             self.failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            self.state = CircuitState.OPEN
            print(f"[CircuitBreaker:{self.name}] Circuit OPEN ({self.failure_count} failures)")
    
    def get_state(self) -> dict:
        """Get current state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "half_open_calls": self.half_open_calls,
        }


# Global circuit breaker for research agent
research_circuit_breaker = CircuitBreaker(
    name="research_agent",
    failure_threshold=3,      # Open after 3 consecutive failures
    recovery_timeout=60.0,    # Try recovery after 60 seconds
    half_open_max_calls=1     # Test with 1 call
)


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global research agent circuit breaker."""
    return research_circuit_breaker
