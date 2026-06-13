# A2A Customer Service Agent - Quick Reference

## System Status Commands

```bash
# Check all agents are running
docker compose ps

# View agent health
curl http://localhost:9001/.well-known/agent.json
curl http://localhost:9002/.well-known/agent.json
curl http://localhost:9003/.well-known/agent.json

# View CS agent skills
curl -s http://localhost:9002/.well-known/agent.json | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Skills: {len(d[\"skills\"])}')"
```

## Development Commands

```bash
# Rebuild and restart
docker compose down && docker compose up --build -d

# View logs
docker compose logs -f
docker compose logs -f cs-agent
docker compose logs -f research-agent

# Run tests
bash tests/run_tests.sh

# Run evaluation
python3 eval/run_evaluation.py --smoke-only
```

## Key Features

### 1. Intent Classification
```python
# In agent or tool
from cs_agent.research_client_tool import classify_research_intent

result = classify_research_intent("What are all the exceptions?")
# Returns: {
#   "needs_research": True,
#   "confidence": "high",
#   "reason": "Research keywords detected: ['exceptions']",
#   "suggested_approach": "Escalate to Research Agent"
# }
```

### 2. Circuit Breaker
```python
from cs_agent.circuit_breaker import get_circuit_breaker

cb = get_circuit_breaker()
if cb.can_execute():
    # Call research agent
    result = await consult_research_agent(question)
    cb.record_success()
else:
    # Circuit open, use fallback
    result = "Research unavailable, using direct search"

# Check state
print(cb.get_state())
```

### 3. Query Expansion
```python
from cs_agent.rag_tools import expand_query, kb_search_enhanced

# Expand query with synonyms
expanded = expand_query("overdraft fee")
# Returns: ["overdraft fee", "overdraft NSF fee", "negative balance fee", ...]

# Search with expansion
results = kb_search_enhanced("overdraft fee", top_k=5)
```

### 4. Response Validation
```python
from cs_agent.response_validator import validate_response, self_correct

# Validate an answer
is_valid, corrected = await validate_response(
    question="What's my balance?",
    proposed_answer="Your balance is $100",
    search_results=kb_results
)

# Auto-correct with retry
final_answer = await self_correct(
    question=question,
    initial_answer=draft_answer,
    search_results=kb_results,
    max_iterations=2
)
```

### 5. Tool Formatting
```python
from cs_agent.tool_formatters import format_tool_result

# Format any tool result
formatted = format_tool_result("get_account_balance", raw_result)
# Returns: "Account Balance: $1,234.56"
```

### 6. Conversation Memory
```python
from cs_agent.conversation_memory import get_memory

# Get or create memory for session
memory = get_memory(session_id)

# Add conversation turn
memory.add_turn("user", "I need to check my balance")
memory.add_turn("assistant", "Let me help you with that")

# Get context for response
context = memory.get_context()
# Returns summary + key facts + recent turns

# Check if user verified
if memory.is_verified():
    # Can access sensitive info
    pass
```

### 7. Performance Monitoring
```python
from cs_agent.monitoring import get_monitor

monitor = get_monitor()

# Record metrics
monitor.record_request(duration=2.5, success=True)
monitor.record_tool_call("kb_search", duration=0.8, success=True)
monitor.record_research_call(query, duration=5.2, classification=class_result)

# Get dashboard
print(monitor.get_dashboard())
```

### 8. Failure Tracking
```python
from cs_agent.failure_tracker import get_failure_tracker

tracker = get_failure_tracker()

# Log a failure
tracker.log_failure(
    query="complex question",
    failure_type="timeout",
    context={"tools_used": ["research"]}
)

# Get adjustment recommendation
adjustment = tracker.get_adjustment(current_query)
# Returns: {"adjustment": "use_research_agent", ...}

# Get statistics
stats = tracker.get_statistics()
```

## Architecture Overview

```
User → Personal Agent (9001)
           ↓ A2A
      CS Agent (9002)
       ├─ KB Search (3 types)
       ├─ Research Client
       │       ↓ A2A
       │  Research Agent (9003)
       │
       ├─ Intent Classification
       ├─ Circuit Breaker
       ├─ Response Validation
       ├─ Conversation Memory
       └─ Performance Monitor
```

## File Locations

| Component | Path |
|-----------|------|
| CS Agent | `cs_agent/agent.py` (19 tools) |
| Research Agent | `research_agent/agent.py` |
| Personal Agent | `personal_agent/agent.py` |
| Intent Classification | `cs_agent/research_client_tool.py` |
| Circuit Breaker | `cs_agent/circuit_breaker.py` |
| Tool Formatters | `cs_agent/tool_formatters.py` |
| Response Validation | `cs_agent/response_validator.py` |
| Failure Tracking | `cs_agent/failure_tracker.py` |
| Conversation Memory | `cs_agent/conversation_memory.py` |
| Performance Monitor | `cs_agent/monitoring.py` |
| Query Expansion | `cs_agent/rag_tools.py` |
| Tests | `tests/` |
| Evaluation | `eval/` |

## Configuration

### Environment Variables
```bash
# Required
export GOOGLE_API_KEY=your_key
export MODEL=gemini-3.5-flash

# Optional (defaults work with docker-compose)
export ENV_API_URL=http://host.docker.internal:8090
export CS_AGENT_URL=http://host.docker.internal:8090/cs-agent
export RESEARCH_AGENT_URL=http://research-agent:9003
```

### Docker Compose
```bash
# Start all services
docker compose up --build -d

# Stop
docker compose down

# View logs
docker compose logs -f [service]

# Restart single service
docker compose restart cs-agent
```

## Testing

```bash
# Run unit tests
bash tests/run_tests.sh

# Run specific test file
python3 -m pytest tests/test_intent_classification.py -v

# Run integration tests (requires agents running)
python3 -m pytest tests/integration_test.py -v

# Run evaluation
python3 eval/run_evaluation.py --smoke-only
python3 eval/run_evaluation.py  # Full evaluation
```

## Troubleshooting

### Agents Not Starting
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker compose logs cs-agent

# Rebuild from scratch
docker compose down -v
docker compose up --build -d
```

### Import Errors
```bash
# Rebuild specific agent
docker compose build cs-agent --no-cache
docker compose up -d cs-agent
```

### Circuit Breaker Open
```bash
# Check circuit breaker state
docker compose exec cs-agent python3 -c "
from circuit_breaker import get_circuit_breaker
cb = get_circuit_breaker()
print(cb.get_state())
"

# Reset by restarting
docker compose restart cs-agent
```

### Performance Issues
```bash
# Check response times
docker compose logs cs-agent | grep "duration"

# View monitoring dashboard
docker compose exec cs-agent python3 -c "
from monitoring import get_monitor
print(get_monitor().get_dashboard())
"
```

## Performance Tuning

### Circuit Breaker Settings
```python
# In cs_agent/circuit_breaker.py
research_circuit_breaker = CircuitBreaker(
    name="research_agent",
    failure_threshold=3,      # Lower = more sensitive
    recovery_timeout=60.0,    # Seconds before retry
    half_open_max_calls=1     # Test calls when recovering
)
```

### Query Expansion
```python
# In cs_agent/rag_tools.py
QUERY_EXPANSIONS = {
    # Add more synonyms for your domain
    "new_term": ["synonym1", "synonym2"],
}
```

### Intent Classification
```python
# In cs_agent/research_client_tool.py
RESEARCH_KEYWORDS = [
    # Add more keywords
    "your_keyword",
]
```

## Common Patterns

### Pattern 1: Smart Research Escalation
```python
# Check if needs research
classification = classify_research_intent(user_query)

if classification["needs_research"]:
    # Check circuit breaker
    if is_research_agent_available():
        result = await smart_consult_research(user_query, context)
    else:
        result = await deep_kb_search(user_query)
else:
    result = await kb_search_enhanced(user_query)
```

### Pattern 2: Validated Response
```python
# Generate draft
draft = await generate_response(query)

# Validate if needed
if should_validate(query, draft):
    is_valid, final = await self_correct(query, draft, search_results)
else:
    final = draft

# Format tool results
final = format_tool_result("response", final)
```

### Pattern 3: Memory-Enhanced Conversation
```python
# Get memory
memory = get_memory(session_id)

# Add user message
memory.add_turn("user", user_message)

# Get context for LLM
context = memory.get_context()

# Generate response with context
response = await generate_with_context(user_message, context)

# Store assistant response
memory.add_turn("assistant", response)
```

## Metrics to Monitor

| Metric | Target | Where to Check |
|--------|--------|----------------|
| Success Rate | > 70% | `eval/run_evaluation.py` |
| Avg Response Time | < 30s | `monitoring.get_dashboard()` |
| Research Escalation | 20-40% | Intent classification logs |
| Classification Accuracy | > 85% | `monitoring.get_dashboard()` |
| Circuit Breaker | Mostly CLOSED | `circuit_breaker.get_state()` |
| Error Rate | < 5% | `failure_tracker.get_statistics()` |

## Support

For issues:
1. Check logs: `docker compose logs`
2. Run tests: `bash tests/run_tests.sh`
3. Check FEATURES.md for detailed documentation
4. Review MODEL_EXAMPLE_ANALYSIS.md for patterns
