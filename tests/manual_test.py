"""Manual tests for A2A Customer Service Agent.

Simple tests that don't require pytest.
Run with: python3 tests/manual_test.py
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cs_agent.research_client_tool import classify_research_intent
from cs_agent.rag_tools import expand_query
from cs_agent.circuit_breaker import CircuitBreaker, CircuitState


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    END = '\033[0m'


def test_intent_classification():
    """Test intent classification."""
    print(f"{Colors.YELLOW}Testing Intent Classification...{Colors.END}")
    
    tests = [
        ("What's my balance?", False, "Simple balance query"),
        ("What are all the exceptions?", True, "Policy exceptions query"),
        ("Compare account types", True, "Comparison query"),
        ("How do I dispute?", True, "Procedure query"),
        ("Is my card active?", False, "Status check"),
    ]
    
    passed = 0
    for query, expected, description in tests:
        result = classify_research_intent(query)
        actual = result["needs_research"]
        
        if actual == expected:
            print(f"{Colors.GREEN}✓{Colors.END} {description}")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.END} {description}")
            print(f"  Expected: {expected}, Got: {actual}")
    
    return passed, len(tests)


def test_query_expansion():
    """Test query expansion."""
    print(f"\n{Colors.YELLOW}Testing Query Expansion...{Colors.END}")
    
    tests = [
        ("overdraft fee", ["NSF", "negative balance"], "Overdraft expansion"),
        ("dispute transaction", ["fraud", "unauthorized"], "Dispute expansion"),
        ("referral bonus", ["invite", "refer a friend"], "Referral expansion"),
    ]
    
    passed = 0
    for query, expected_synonyms, description in tests:
        expanded = expand_query(query)
        
        # Check if any expected synonym is present
        found = any(
            any(syn in e for e in expanded)
            for syn in expected_synonyms
        )
        
        if found:
            print(f"{Colors.GREEN}✓{Colors.END} {description}")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.END} {description}")
            print(f"  Expanded to: {expanded}")
    
    return passed, len(tests)


def test_circuit_breaker():
    """Test circuit breaker."""
    print(f"\n{Colors.YELLOW}Testing Circuit Breaker...{Colors.END}")
    
    passed = 0
    total = 0
    
    # Test 1: Initial state
    total += 1
    cb = CircuitBreaker("test", failure_threshold=3)
    if cb.state == CircuitState.CLOSED and cb.can_execute():
        print(f"{Colors.GREEN}✓{Colors.END} Initial state is CLOSED")
        passed += 1
    else:
        print(f"{Colors.RED}✗{Colors.END} Initial state wrong")
    
    # Test 2: Single failure doesn't open
    total += 1
    cb.record_failure()
    if cb.state == CircuitState.CLOSED:
        print(f"{Colors.GREEN}✓{Colors.END} Single failure doesn't open circuit")
        passed += 1
    else:
        print(f"{Colors.RED}✗{Colors.END} Circuit opened too early")
    
    # Test 3: Multiple failures open circuit
    total += 1
    cb.record_failure()
    cb.record_failure()
    if cb.state == CircuitState.OPEN and not cb.can_execute():
        print(f"{Colors.GREEN}✓{Colors.END} Circuit opens after threshold failures")
        passed += 1
    else:
        print(f"{Colors.RED}✗{Colors.END} Circuit didn't open")
    
    # Test 4: State tracking
    total += 1
    state = cb.get_state()
    if "state" in state and "failure_count" in state:
        print(f"{Colors.GREEN}✓{Colors.END} State tracking works")
        passed += 1
    else:
        print(f"{Colors.RED}✗{Colors.END} State tracking broken")
    
    return passed, total


def main():
    """Run all tests."""
    print("=" * 50)
    print("A2A CUSTOMER SERVICE AGENT - MANUAL TESTS")
    print("=" * 50)
    
    # Run tests
    intent_passed, intent_total = test_intent_classification()
    expansion_passed, expansion_total = test_query_expansion()
    circuit_passed, circuit_total = test_circuit_breaker()
    
    # Summary
    total_passed = intent_passed + expansion_passed + circuit_passed
    total_tests = intent_total + expansion_total + circuit_total
    
    print(f"\n{'=' * 50}")
    print(f"RESULTS: {total_passed}/{total_tests} passed")
    
    if total_passed == total_tests:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
