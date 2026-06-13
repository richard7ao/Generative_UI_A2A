"""Performance monitoring and metrics collection.

Tracks agent performance, response times, and success rates.
Useful for debugging and optimization.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from statistics import mean, median


@dataclass
class Metric:
    """A single metric measurement."""
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class PerformanceMonitor:
    """Monitors agent performance metrics.
    
    Tracks:
    - Response times
    - Success/failure rates
    - Tool usage patterns
    - Research agent escalation rate
    - Query classification accuracy
    """
    
    def __init__(self, max_history: int = 1000):
        """Initialize monitor.
        
        Args:
            max_history: Maximum metrics to keep per category
        """
        self.max_history = max_history
        
        # Metric storage
        self.response_times: deque = deque(maxlen=max_history)
        self.tool_calls: deque = deque(maxlen=max_history)
        self.research_calls: deque = deque(maxlen=max_history)
        self.errors: deque = deque(maxlen=max_history)
        self.classifications: deque = deque(maxlen=max_history)
        
        # Counters
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Tool usage counts
        self.tool_usage: Dict[str, int] = defaultdict(int)
    
    def record_request(self, duration: float, success: bool, metadata: Dict = None):
        """Record a request completion.
        
        Args:
            duration: Request duration in seconds
            success: Whether request succeeded
            metadata: Additional context
        """
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.response_times.append(Metric(
            value=duration,
            metadata=metadata or {}
        ))
    
    def record_tool_call(self, tool_name: str, duration: float, success: bool):
        """Record a tool call.
        
        Args:
            tool_name: Name of the tool
            duration: Call duration
            success: Whether call succeeded
        """
        self.tool_calls.append(Metric(
            value=duration,
            metadata={"tool": tool_name, "success": success}
        ))
        
        self.tool_usage[tool_name] += 1
    
    def record_research_call(self, query: str, duration: float, classification: Dict):
        """Record a research agent call.
        
        Args:
            query: The query sent to research
            duration: Call duration
            classification: Intent classification result
        """
        self.research_calls.append(Metric(
            value=duration,
            metadata={
                "query": query[:50],
                "classification": classification,
            }
        ))
    
    def record_error(self, error_type: str, message: str, context: Dict = None):
        """Record an error.
        
        Args:
            error_type: Type of error (timeout, exception, etc.)
            message: Error message
            context: Additional context
        """
        self.errors.append(Metric(
            value=1.0,
            metadata={
                "type": error_type,
                "message": message,
                "context": context or {}
            }
        ))
    
    def record_classification(self, query: str, classification: Dict, actually_used_research: bool):
        """Record intent classification accuracy.
        
        Args:
            query: The classified query
            classification: Classification result
            actually_used_research: Whether research was actually called
        """
        predicted = classification.get("needs_research", False)
        correct = predicted == actually_used_research
        
        self.classifications.append(Metric(
            value=1.0 if correct else 0.0,
            metadata={
                "query": query[:50],
                "predicted": predicted,
                "actual": actually_used_research,
                "confidence": classification.get("confidence", "unknown")
            }
        ))
    
    def get_stats(self) -> Dict:
        """Get current performance statistics.
        
        Returns:
            Dict with comprehensive stats
        """
        stats = {
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": self._calc_success_rate()
            },
            "response_times": self._calc_response_stats(),
            "tools": self._calc_tool_stats(),
            "research": self._calc_research_stats(),
            "errors": self._calc_error_stats(),
            "classification_accuracy": self._calc_classification_accuracy(),
        }
        
        return stats
    
    def _calc_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def _calc_response_stats(self) -> Dict:
        """Calculate response time statistics."""
        if not self.response_times:
            return {"count": 0}
        
        times = [m.value for m in self.response_times]
        return {
            "count": len(times),
            "mean": mean(times),
            "median": median(times),
            "min": min(times),
            "max": max(times),
            "p95": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times)
        }
    
    def _calc_tool_stats(self) -> Dict:
        """Calculate tool usage statistics."""
        if not self.tool_calls:
            return {"count": 0}
        
        # Group by tool
        by_tool = defaultdict(lambda: {"times": [], "success": 0, "fail": 0})
        
        for metric in self.tool_calls:
            tool = metric.metadata.get("tool", "unknown")
            by_tool[tool]["times"].append(metric.value)
            if metric.metadata.get("success"):
                by_tool[tool]["success"] += 1
            else:
                by_tool[tool]["fail"] += 1
        
        # Calculate per-tool stats
        tool_stats = {}
        for tool, data in by_tool.items():
            times = data["times"]
            tool_stats[tool] = {
                "calls": len(times),
                "avg_time": mean(times) if times else 0,
                "success_rate": data["success"] / (data["success"] + data["fail"]) if (data["success"] + data["fail"]) > 0 else 1.0
            }
        
        return {
            "total_calls": len(self.tool_calls),
            "by_tool": tool_stats,
            "usage_counts": dict(self.tool_usage)
        }
    
    def _calc_research_stats(self) -> Dict:
        """Calculate research agent usage statistics."""
        if not self.research_calls:
            return {"count": 0}
        
        times = [m.value for m in self.research_calls]
        
        # Count by classification confidence
        confidence_counts = defaultdict(int)
        for metric in self.research_calls:
            conf = metric.metadata.get("classification", {}).get("confidence", "unknown")
            confidence_counts[conf] += 1
        
        return {
            "count": len(self.research_calls),
            "avg_duration": mean(times),
            "by_confidence": dict(confidence_counts),
            "escalation_rate": len(self.research_calls) / max(self.total_requests, 1)
        }
    
    def _calc_error_stats(self) -> Dict:
        """Calculate error statistics."""
        if not self.errors:
            return {"count": 0}
        
        by_type = defaultdict(int)
        recent_errors = []
        
        for metric in self.errors:
            error_type = metric.metadata.get("type", "unknown")
            by_type[error_type] += 1
            
            # Keep recent errors (last hour)
            if time.time() - metric.timestamp < 3600:
                recent_errors.append(metric.metadata.get("message", "unknown"))
        
        return {
            "total": len(self.errors),
            "by_type": dict(by_type),
            "recent_hour": len(recent_errors),
            "recent_examples": recent_errors[:5]  # Last 5
        }
    
    def _calc_classification_accuracy(self) -> Dict:
        """Calculate intent classification accuracy."""
        if not self.classifications:
            return {"count": 0}
        
        scores = [m.value for m in self.classifications]
        
        # By confidence level
        by_confidence = defaultdict(lambda: {"correct": 0, "total": 0})
        for metric in self.classifications:
            conf = metric.metadata.get("confidence", "unknown")
            by_confidence[conf]["total"] += 1
            if metric.value > 0.5:
                by_confidence[conf]["correct"] += 1
        
        accuracy_by_conf = {}
        for conf, data in by_confidence.items():
            accuracy_by_conf[conf] = {
                "accuracy": data["correct"] / data["total"] if data["total"] > 0 else 0,
                "count": data["total"]
            }
        
        return {
            "total_classified": len(scores),
            "overall_accuracy": mean(scores),
            "by_confidence": accuracy_by_conf
        }
    
    def get_dashboard(self) -> str:
        """Get a formatted dashboard string for display.
        
        Returns:
            Formatted dashboard
        """
        stats = self.get_stats()
        
        lines = [
            "=" * 50,
            "A2A AGENT PERFORMANCE DASHBOARD",
            "=" * 50,
            "",
            f"📊 Requests: {stats['requests']['total']} total, "
            f"{stats['requests']['success_rate']:.1%} success",
            "",
            "⏱️  Response Times:",
        ]
        
        rt = stats['response_times']
        if rt['count'] > 0:
            lines.extend([
                f"   Mean: {rt['mean']:.2f}s, Median: {rt['median']:.2f}s",
                f"   P95: {rt['p95']:.2f}s, Max: {rt['max']:.2f}s",
            ])
        else:
            lines.append("   No data yet")
        
        lines.extend([
            "",
            "🔧 Tool Usage:",
        ])
        
        tools = stats['tools']
        if tools['total_calls'] > 0:
            for tool, data in sorted(tools['by_tool'].items(), 
                                    key=lambda x: x[1]['calls'], reverse=True)[:5]:
                lines.append(f"   {tool}: {data['calls']} calls, "
                           f"{data['avg_time']:.2f}s avg")
        else:
            lines.append("   No tool calls yet")
        
        lines.extend([
            "",
            "🔬 Research Agent:",
        ])
        
        research = stats['research']
        if research['count'] > 0:
            lines.append(f"   {research['count']} calls, "
                        f"{research['escalation_rate']:.1%} escalation rate")
            lines.append(f"   Avg duration: {research['avg_duration']:.2f}s")
        else:
            lines.append("   No research calls yet")
        
        lines.extend([
            "",
            "🎯 Classification Accuracy:",
        ])
        
        cls = stats['classification_accuracy']
        if cls['count'] > 0:
            lines.append(f"   Overall: {cls['overall_accuracy']:.1%}")
            for conf, data in cls['by_confidence'].items():
                lines.append(f"   {conf}: {data['accuracy']:.1%} ({data['count']} samples)")
        else:
            lines.append("   No classifications yet")
        
        lines.extend([
            "",
            "⚠️  Errors:",
        ])
        
        errors = stats['errors']
        if errors['total'] > 0:
            lines.append(f"   Total: {errors['total']}, Recent (1h): {errors['recent_hour']}")
            for error_type, count in errors['by_type'].items():
                lines.append(f"   {error_type}: {count}")
        else:
            lines.append("   No errors - system healthy!")
        
        lines.extend([
            "",
            "=" * 50,
        ])
        
        return "\n".join(lines)


# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def reset_monitor():
    """Reset the global monitor (useful for testing)."""
    global _monitor
    _monitor = PerformanceMonitor()
