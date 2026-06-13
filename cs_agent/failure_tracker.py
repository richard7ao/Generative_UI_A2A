"""Failure pattern tracking and learning for continuous improvement.

Based on Advanced Strategy #10: Failure Pattern Learning
Tracks failures to automatically adjust behavior over time.
"""

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

# Store failure patterns
FAILURE_LOG_PATH = Path("/tmp/a2a_failure_log.json")


class FailurePattern:
    """Represents a single failure occurrence."""
    
    def __init__(
        self,
        query: str,
        failure_type: str,
        context: Dict,
        timestamp: float = None
    ):
        self.query = query
        self.failure_type = failure_type
        self.context = context
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "failure_type": self.failure_type,
            "context": self.context,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FailurePattern":
        return cls(
            query=data["query"],
            failure_type=data["failure_type"],
            context=data.get("context", {}),
            timestamp=data.get("timestamp", time.time())
        )


class FailureTracker:
    """Tracks and learns from failures to improve agent behavior.
    
    Example patterns tracked:
    - Timeout failures (which queries timeout)
    - Wrong answers (when validation fails)
    - KB search failures (queries with no results)
    - Tool calling errors (wrong tool or arguments)
    """
    
    def __init__(self):
        self.patterns: List[FailurePattern] = []
        self.pattern_counts: Dict[str, int] = defaultdict(int)
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load historical failures from disk."""
        if FAILURE_LOG_PATH.exists():
            try:
                with open(FAILURE_LOG_PATH) as f:
                    data = json.load(f)
                    for item in data.get("patterns", []):
                        pattern = FailurePattern.from_dict(item)
                        self.patterns.append(pattern)
                        self.pattern_counts[pattern.failure_type] += 1
            except Exception as e:
                print(f"[FailureTracker] Error loading history: {e}")
    
    def _save_to_disk(self):
        """Save failures to disk for persistence."""
        try:
            data = {
                "patterns": [p.to_dict() for p in self.patterns[-100:]]  # Keep last 100
            }
            with open(FAILURE_LOG_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[FailureTracker] Error saving history: {e}")
    
    def log_failure(
        self,
        query: str,
        failure_type: str,
        context: Dict = None
    ):
        """Log a failure for pattern analysis.
        
        Args:
            query: The query that failed
            failure_type: Category of failure (timeout, wrong_answer, no_results, etc.)
            context: Additional context (agent_called, tools_used, etc.)
        """
        pattern = FailurePattern(
            query=query,
            failure_type=failure_type,
            context=context or {}
        )
        
        self.patterns.append(pattern)
        self.pattern_counts[failure_type] += 1
        
        # Save periodically (every 5 failures)
        if len(self.patterns) % 5 == 0:
            self._save_to_disk()
        
        print(f"[FailureTracker] Logged {failure_type} failure for: {query[:50]}...")
    
    def get_adjustment(self, query: str) -> Optional[Dict]:
        """Get behavioral adjustments based on failure history.
        
        Args:
            query: The current query
            
        Returns:
            Adjustment dict if pattern detected, None otherwise
        """
        query_lower = query.lower()
        
        # Check for timeout-prone patterns
        timeout_rate = self._get_failure_rate("timeout", window=10)
        if timeout_rate > 0.5:
            return {
                "adjustment": "reduce_complexity",
                "suggestion": "Break query into sub-queries or simplify",
                "reason": f"High timeout rate: {timeout_rate:.0%}"
            }
        
        # Check for queries that consistently fail
        similar_failures = self._find_similar_failures(query_lower)
        if similar_failures >= 3:
            return {
                "adjustment": "use_research_agent",
                "suggestion": "Route directly to Research Agent",
                "reason": f"Query pattern failed {similar_failures} times previously"
            }
        
        # Check for KB search failures
        no_results_rate = self._get_failure_rate("no_results", window=5)
        if no_results_rate > 0.6:
            return {
                "adjustment": "expand_query",
                "suggestion": "Use query expansion and synonyms",
                "reason": f"High no-results rate: {no_results_rate:.0%}"
            }
        
        return None
    
    def _get_failure_rate(self, failure_type: str, window: int = 10) -> float:
        """Calculate failure rate for a specific type.
        
        Args:
            failure_type: Type of failure to check
            window: Number of recent patterns to consider
            
        Returns:
            Failure rate (0.0 to 1.0)
        """
        recent = [p for p in self.patterns[-window:] if p.failure_type == failure_type]
        return len(recent) / max(len(self.patterns[-window:]), 1)
    
    def _find_similar_failures(self, query: str) -> int:
        """Count how many times similar queries have failed.
        
        Args:
            query: Current query to compare
            
        Returns:
            Count of similar failed queries
        """
        count = 0
        
        # Extract key terms (words > 4 chars)
        key_terms = [w for w in query.split() if len(w) > 4]
        
        for pattern in self.patterns:
            if pattern.failure_type == "wrong_answer":
                pattern_terms = [w for w in pattern.query.lower().split() if len(w) > 4]
                # Count overlapping terms
                overlap = len(set(key_terms) & set(pattern_terms))
                if overlap >= 2:  # At least 2 shared terms
                    count += 1
        
        return count
    
    def get_statistics(self) -> Dict:
        """Get failure statistics for monitoring.
        
        Returns:
            Dict with failure stats
        """
        total = len(self.patterns)
        if total == 0:
            return {"total_failures": 0, "by_type": {}}
        
        # Count by type
        by_type = {}
        for pattern in self.patterns:
            by_type[pattern.failure_type] = by_type.get(pattern.failure_type, 0) + 1
        
        # Recent failures (last hour)
        one_hour_ago = time.time() - 3600
        recent = [p for p in self.patterns if p.timestamp > one_hour_ago]
        
        return {
            "total_failures": total,
            "recent_failures_1h": len(recent),
            "by_type": by_type,
            "top_patterns": sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def should_escalate(self, query: str) -> bool:
        """Quick check if query should be escalated based on history.
        
        Args:
            query: Current query
            
        Returns:
            True if escalation recommended
        """
        adjustment = self.get_adjustment(query)
        if adjustment and adjustment["adjustment"] in ["use_research_agent", "reduce_complexity"]:
            return True
        return False


# Global failure tracker instance
_failure_tracker = None


def get_failure_tracker() -> FailureTracker:
    """Get or create global failure tracker."""
    global _failure_tracker
    if _failure_tracker is None:
        _failure_tracker = FailureTracker()
    return _failure_tracker
