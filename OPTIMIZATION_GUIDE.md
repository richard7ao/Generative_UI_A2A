# A2A Customer Service Agent - Optimization Guide

## Performance Tuning Checklist

### Pre-Deployment Optimizations

#### 1. Intent Classification Thresholds
**File**: `cs_agent/research_client_tool.py`

```python
# Adjust these based on train split results
RESEARCH_KEYWORDS = [
    # Add/remove keywords based on:
    # - False positives (simple queries calling research)
    # - False negatives (complex queries not calling research)
]

SIMPLE_QUERY_PATTERNS = [
    # Add patterns for queries that definitely don't need research
]
```

**Metrics to Monitor**:
- Research escalation rate (target: 20-40%)
- Classification accuracy from monitoring dashboard

**Tuning**:
```bash
# Check current escalation rate
docker compose exec cs-agent python3 -c "
from monitoring import get_monitor
m = get_monitor()
print(m.get_stats()['research'])
"
```

#### 2. Circuit Breaker Sensitivity
**File**: `cs_agent/circuit_breaker.py`

```python
research_circuit_breaker = CircuitBreaker(
    name="research_agent",
    failure_threshold=3,      # ← Adjust: Lower = more sensitive
    recovery_timeout=60.0,    # ← Adjust: Seconds before retry
    half_open_max_calls=1     # ← Adjust: Test calls when recovering
)
```

**When to Adjust**:
- If research agent intermittently slow → Increase threshold to 5
- If cascading failures frequent → Decrease timeout to 30s
- If recovery flaky → Increase half_open_max_calls to 2

#### 3. Query Expansion Synonyms
**File**: `cs_agent/rag_tools.py`

```python
QUERY_EXPANSIONS = {
    # Add domain-specific synonyms
    "your_term": ["synonym1", "synonym2", "synonym3"],
}
```

**When to Add**:
- Queries with no results that should match
- User feedback about missing information
- Analysis of failed searches

#### 4. Response Validation Thresholds
**File**: `cs_agent/response_validator.py`

```python
def should_validate(question: str, answer: str) -> bool:
    # Current: validates if >300 chars or has numbers
    # Adjust based on:
    # - Validation pass rate
    # - User feedback on accuracy
```

#### 5. Conversation Memory Settings
**File**: `cs_agent/conversation_memory.py`

```python
class ConversationMemory:
    def __init__(self, max_history: int = 10):  # ← Adjust
        self.summary_interval: float = 300  # ← Seconds between summaries
```

## Runtime Optimization

### Memory Usage
```bash
# Monitor container memory
docker stats --no-stream

# If high memory:
# 1. Reduce Redis memory limit
# 2. Clear old conversation memories
# 3. Reduce failure log retention
```

### Response Time Optimization

#### 1. KB Search Performance
```python
# In cs_agent/rag_tools.py
# Reduce top_k for faster searches
def kb_search_bm25(query: str, top_k: int = 3):  # Was 5
    ...
```

#### 2. Parallel Tool Calls
```python
# Use asyncio.gather for independent operations
results = await asyncio.gather(
    kb_search_bm25(query),
    kb_search_vector(query),
    return_exceptions=True
)
```

#### 3. Research Agent Timeout
```python
# In cs_agent/research_client_tool.py
_TIMEOUT_S = 180.0  # Reduce from 300s if needed
```

### Database Optimization (Redis)

```bash
# Monitor Redis performance
docker compose exec redis redis-cli INFO stats

# Key metrics:
# - keyspace_hits / keyspace_misses (cache hit rate)
# - total_commands_processed (throughput)
```

## Monitoring & Alerting

### Key Metrics to Watch

| Metric | Warning Threshold | Critical Threshold |
|--------|-------------------|-------------------|
| Success Rate | < 70% | < 50% |
| Avg Response Time | > 10s | > 30s |
| Research Escalation | > 60% | > 80% |
| Circuit Breaker | OPEN > 5 min | Always OPEN |
| Error Rate | > 5% | > 15% |
| Classification Accuracy | < 80% | < 60% |

### Automated Checks
```bash
# Add to crontab for monitoring
*/5 * * * * cd /path/to/project && python3 check_health.py
```

```python
# check_health.py
from monitoring import get_monitor

m = get_monitor()
stats = m.get_stats()

if stats['requests']['success_rate'] < 0.7:
    print("ALERT: Success rate below 70%")
    # Send alert
```

## A/B Testing Features

### Test Different Intent Classification
```python
# In cs_agent/research_client_tool.py
# Create test variants

def classify_v1(query):  # Current
    ...

def classify_v2(query):  # New approach
    ...

# Randomly route
import random
classifier = classify_v1 if random.random() < 0.5 else classify_v2
```

### Compare Query Expansion Variants
```python
# Test synonym sets
QUERY_EXPANSIONS_V1 = {...}  # Current
QUERY_EXPANSIONS_V2 = {...}  # New

# Track which performs better
```

## Scaling Considerations

### Horizontal Scaling
```yaml
# docker-compose.yml
# Scale CS agents
  cs-agent:
    deploy:
      replicas: 2
```

**Considerations**:
- Session affinity required (same agent per session)
- Redis shared state
- Circuit breaker per instance

### Vertical Scaling
```yaml
# Increase resources
cs-agent:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

## Debugging Tools

### 1. Intent Classification Debug
```bash
docker compose exec cs-agent python3 -c "
from research_client_tool import classify_research_intent
result = classify_research_intent('Your test query')
print(result)
"
```

### 2. Query Expansion Debug
```bash
docker compose exec cs-agent python3 -c "
from rag_tools import expand_query
print(expand_query('overdraft fee'))
"
```

### 3. Circuit Breaker State
```bash
docker compose exec cs-agent python3 -c "
from circuit_breaker import get_circuit_breaker
print(get_circuit_breaker().get_state())
"
```

### 4. Performance Dashboard
```bash
docker compose exec cs-agent python3 -c "
from monitoring import get_monitor
print(get_monitor().get_dashboard())
"
```

### 5. Failure Analysis
```bash
docker compose exec cs-agent python3 -c "
from failure_tracker import get_failure_tracker
print(get_failure_tracker().get_statistics())
"
```

## Common Issues & Fixes

### Issue: Too Many Research Calls
**Symptoms**: Research escalation > 50%

**Diagnosis**:
```bash
python3 -c "
from monitoring import get_monitor
stats = get_monitor().get_stats()
print(f\"Escalation rate: {stats['research']['escalation_rate']:.1%}\")
"
```

**Fix**: Add more SIMPLE_QUERY_PATTERNS to `research_client_tool.py`

### Issue: Research Agent Timeouts
**Symptoms**: Circuit breaker frequently OPEN

**Diagnosis**:
```bash
docker compose logs research-agent | grep -i timeout
```

**Fix**:
1. Increase `_TIMEOUT_S` if research is slow but correct
2. Decrease `failure_threshold` if research is failing
3. Add caching to `research_tools.py`

### Issue: Low Classification Accuracy
**Symptoms**: Validation shows < 80% accuracy

**Diagnosis**:
```bash
python3 -c "
from monitoring import get_monitor
stats = get_monitor().get_stats()
for conf, data in stats['classification_accuracy']['by_confidence'].items():
    print(f'{conf}: {data['accuracy']:.1%}')
"
```

**Fix**:
1. Review misclassified queries
2. Adjust keyword patterns
3. Add new keywords based on failure patterns

### Issue: High Memory Usage
**Symptoms**: Container memory > 2GB

**Diagnosis**:
```bash
docker stats --no-stream
```

**Fix**:
1. Clear old conversation memories
2. Reduce `max_history` in ConversationMemory
3. Clear failure logs periodically

### Issue: Slow Response Times
**Symptoms**: P95 response time > 30s

**Diagnosis**:
```bash
python3 -c "
from monitoring import get_monitor
rt = get_monitor().get_stats()['response_times']
print(f\"P95: {rt['p95']:.2f}s\")
"
```

**Fix**:
1. Reduce `top_k` in KB searches
2. Add caching layer
3. Optimize research agent queries
4. Use query expansion only when needed

## Performance Baselines

After running train split, record these:

```json
{
  "baseline_metrics": {
    "success_rate": 0.75,
    "avg_response_time": 4.5,
    "research_escalation_rate": 0.35,
    "classification_accuracy": 0.88,
    "circuit_breaker_openings": 2
  },
  "tuning_changes": {
    "failure_threshold": 3,
    "recovery_timeout": 60,
    "max_history": 10,
    "kb_top_k": 5
  }
}
```

## Continuous Improvement Loop

```
1. Run Evaluation → 2. Analyze Failures → 3. Identify Patterns
        ↑                                      ↓
        ←←←← 4. Tune Parameters ←←←←←←← 5. Implement Fixes
```

### Weekly Tasks
- [ ] Review failure tracker statistics
- [ ] Check classification accuracy trends
- [ ] Analyze slow queries (> 30s)
- [ ] Review user feedback (if available)

### Monthly Tasks
- [ ] Run full train split evaluation
- [ ] Compare metrics to baseline
- [ ] Add new query expansions based on search logs
- [ ] Update intent classification keywords

## Hackathon-Specific Tuning

### For Maximum Score

1. **Success Rate > 70%**
   - Focus on most common query patterns
   - Ensure KB covers all basic scenarios
   - Test identity verification flow

2. **Response Time < 10s Average**
   - Use simple KB search when possible
   - Only call research for truly complex queries
   - Cache frequently accessed data

3. **Research Usage 20-40%**
   - Not too low (wasting capability)
   - Not too high (over-escalating)
   - Fine-tune classification thresholds

4. **No Cascading Failures**
   - Ensure circuit breaker works
   - Have fallbacks for all agents
   - Test degraded operation

### Quick Wins

1. **Add more SIMPLE_QUERY_PATTERNS** (30 min)
2. **Tune circuit breaker thresholds** (15 min)
3. **Add domain-specific query expansions** (30 min)
4. **Optimize KB search top_k** (5 min)
5. **Add response caching** (1 hour)

## Resources

- **Feature Inventory**: `FEATURES.md`
- **Quick Reference**: `QUICK_REFERENCE.md`
- **Testing**: `tests/`
- **Evaluation**: `eval/run_evaluation.py`
