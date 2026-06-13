# A2A Customer Service Agent - Hackathon Submission Checklist

## Pre-Submission Checklist

### ✅ System Verification

- [ ] All 3 agents running (`docker compose ps`)
- [ ] All agents serve agent cards (`/.well-known/agent.json`)
- [ ] CS Agent shows 19 skills
- [ ] No errors in logs (`docker compose logs | grep -i error`)
- [ ] Redis is healthy
- [ ] No crashed containers

### ✅ A2A Harness Tests

```bash
# 1. Smoke test (MUST PASS)
cd /path/to/a2a-hackathon
uv run a2a-hack smoke \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002

# 2. Train split evaluation
uv run a2a-hack run \
  --tasks train \
  --save-to results/final \
  --auto-resume

# 3. View results
uv run tau2 view results/final
```

**Target Metrics**:
- [ ] Success Rate ≥ 70%
- [ ] No contextId errors
- [ ] Avg response time < 30s
- [ ] No agent crashes

### ✅ Code Quality

- [ ] All syntax errors fixed
- [ ] No hardcoded secrets (use env vars)
- [ ] MODEL=gemini-3.5-flash (required)
- [ ] Docker builds successfully
- [ ] No import errors

### ✅ Documentation

- [ ] README.md present and clear
- [ ] Feature documentation complete
- [ ] Code comments for complex logic
- [ ] Architecture diagram (if applicable)

## Submission Package

### Required Files

```
a2a-customer-service-agents/
├── README.md                    # ✓ Required
├── docker-compose.yml           # ✓ Required
├── .env.example                 # ✓ Required
├── FEATURES.md                  # ✓ Detailed features
├── QUICK_REFERENCE.md           # ✓ Developer guide
├── PROJECT_SUMMARY.md           # ✓ Project overview
├── NEXT_ACTIONS.md              # ✓ Testing plan
├── PLAN.md                      # ✓ Strategy document
├── cs_agent/
│   ├── agent.py                 # ✓ Main agent (19 skills)
│   ├── rag_tools.py             # ✓ KB + expansion
│   ├── research_client_tool.py  # ✓ A2A + classification
│   ├── circuit_breaker.py       # ✓ Resilience
│   ├── tool_formatters.py       # ✓ Formatting
│   ├── response_validator.py    # ✓ Validation
│   ├── failure_tracker.py       # ✓ Learning
│   ├── conversation_memory.py   # ✓ Context
│   ├── monitoring.py            # ✓ Metrics
│   ├── env_toolset.py           # ✓ Tools
│   ├── ingest.py                # ✓ Indexing
│   └── main.py                  # ✓ Server
├── research_agent/
│   ├── agent.py                 # ✓ Research agent
│   ├── research_tools.py        # ✓ Deep search
│   ├── ingest.py                # ✓ Indexing
│   └── main.py                  # ✓ Server
├── personal_agent/
│   ├── agent.py                 # ✓ Personal agent
│   ├── cs_client_tool.py        # ✓ A2A client
│   ├── env_toolset.py           # ✓ Tools
│   └── main.py                  # ✓ Server
├── kb/
│   └── policy.md                # ✓ Policies
├── tests/
│   ├── test_intent_classification.py
│   ├── test_circuit_breaker.py
│   ├── test_query_expansion.py
│   ├── integration_test.py
│   └── manual_test.py
└── eval/
    └── run_evaluation.py        # ✓ Eval runner
```

### GitHub Repository Setup

```bash
# 1. Create clean repository
git init

# 2. Add all files
git add .

# 3. Commit
git commit -m "A2A Customer Service Agent - Hackathon Submission

- 3-agent system (Personal, CS, Research)
- 19 CS agent skills
- Advanced features:
  * Intent classification (24 patterns)
  * Query expansion (12 categories)
  * Circuit breaker pattern
  * Response validation
  * Self-correction
  * Conversation memory
  * Performance monitoring
- Comprehensive testing suite
- Full documentation
"

# 4. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/a2a-customer-service-agents.git
git push -u origin main
```

## Evaluation Criteria Alignment

### 1. Correctness (50%)

**What Judges Look For**:
- [ ] Accurate responses to queries
- [ ] Correct tool usage
- [ ] Proper context handling
- [ ] No hallucinated information

**Our Strengths**:
- ✅ Response validation catches errors
- ✅ Self-correction fixes wrong answers
- ✅ KB search ensures factual accuracy
- ✅ Tool formatters ensure clean output

### 2. Efficiency (30%)

**What Judges Look For**:
- [ ] Fast response times
- [ ] Smart escalation (not too much, not too little)
- [ ] Resource efficiency
- [ ] No unnecessary calls

**Our Strengths**:
- ✅ Intent classification prevents over-escalation
- ✅ Query expansion improves search efficiency
- ✅ Circuit breaker prevents timeout cascades
- ✅ Enhanced search reduces retry attempts

### 3. Robustness (10%)

**What Judges Look For**:
- [ ] Error handling
- [ ] Graceful degradation
- [ ] Recovery from failures
- [ ] No crashes

**Our Strengths**:
- ✅ Circuit breaker prevents cascading failures
- ✅ Failure tracking enables learning
- ✅ Conversation memory preserves context
- ✅ Monitoring enables quick diagnosis

### 4. Documentation (10%)

**What Judges Look For**:
- [ ] Clear README
- [ ] Architecture explanation
- [ ] Setup instructions
- [ ] Code comments

**Our Strengths**:
- ✅ 7 comprehensive documentation files
- ✅ Architecture patterns documented
- ✅ Quick reference guide
- ✅ Code well-commented

## Demo Script

### 60-Second Pitch

"We've built a 3-agent customer service system with 19 tools that can handle complex banking queries.

**What makes it special**:
1. **Smart routing** - 24 keyword patterns decide when to escalate
2. **Self-correcting** - Validates answers before sending
3. **Resilient** - Circuit breaker prevents cascade failures
4. **Learning** - Tracks failures to improve over time

**Try it**: Ask 'What are all the exceptions to the overdraft policy?' - it will automatically call the research agent for deep analysis."

### 5-Minute Demo

1. **Show agent cards** (30s)
   ```bash
   curl http://localhost:9002/.well-known/agent.json | jq '.skills | length'
   # Shows 19 skills
   ```

2. **Show intent classification** (1m)
   ```bash
   # Simple query
   # Complex query with research keywords
   ```

3. **Show circuit breaker** (1m)
   ```bash
   # Trigger failure
   # Show circuit state
   # Show graceful fallback
   ```

4. **Show monitoring dashboard** (1m)
   ```bash
   python3 -c "from monitoring import get_monitor; print(get_monitor().get_dashboard())"
   ```

5. **Show train split results** (1.5m)
   ```bash
   uv run tau2 view results/final
   ```

## Last-Minute Fixes

### If Success Rate < 70%

1. **Check intent classification**
   ```bash
   # Look for misclassified queries in logs
   docker compose logs cs-agent | grep "classif"
   ```

2. **Add missing KB coverage**
   - Review failed queries
   - Add to KB if missing

3. **Tune circuit breaker**
   - May be preventing legitimate research calls

### If Response Time > 30s

1. **Reduce KB search top_k**
   ```python
   # In rag_tools.py, change top_k=5 to top_k=3
   ```

2. **Check research agent health**
   ```bash
   docker compose logs research-agent
   ```

3. **Use query expansion selectively**
   - Only expand if initial search fails

### If Research Escalation > 60%

1. **Add more simple query patterns**
   ```python
   # In research_client_tool.py
   SIMPLE_QUERY_PATTERNS.extend([
       "new_simple_pattern",
   ])
   ```

2. **Lower classification threshold**
   - Require 2+ keywords instead of 1

## Submission Checklist (Final)

### 24 Hours Before
- [ ] Run full train split
- [ ] Analyze failure patterns
- [ ] Make final fixes
- [ ] Update documentation

### 12 Hours Before
- [ ] Final smoke test
- [ ] Verify all agents healthy
- [ ] Check all documentation
- [ ] Prepare demo script

### 1 Hour Before
- [ ] Start all agents
- [ ] Run smoke test
- [ ] Verify agent cards
- [ ] Test demo flow

### Submission
- [ ] Submit GitHub URL
- [ ] Verify repo is public
- [ ] Confirm README is clear
- [ ] Submit demo video (if required)

## Post-Submission

### Monitor During Judging
```bash
# Keep agents running
docker compose logs -f

# Monitor metrics
python3 -c "
from monitoring import get_monitor
print(get_monitor().get_dashboard())
"  # Run periodically
```

### If Issues Arise
1. **Quick restart**: `docker compose restart`
2. **Check logs**: `docker compose logs [service]`
3. **Verify health**: `curl http://localhost:9002/.well-known/agent.json`

## Success Criteria

**Minimum Viable**:
- [ ] 3 agents running
- [ ] A2A communication works
- [ ] Basic KB search functional
- [ ] > 50% train success rate

**Competitive**:
- [ ] Intent classification working
- [ ] Research agent escalation
- [ ] > 70% train success rate
- [ ] Documentation complete

**Winning**:
- [ ] All 19 skills functional
- [ ] > 80% train success rate
- [ ] Advanced patterns (circuit breaker, validation)
- [ ] Exceptional documentation
- [ ] Novel features or optimizations

## Emergency Contacts (If Available)

- Team lead: [name]
- Technical lead: [name]
- Documentation: [name]

## Final Reminder

**What Judges See**:
1. Your code (GitHub repo)
2. Your documentation (README, etc.)
3. Your metrics (train split results)
4. Your demo (if applicable)

**Make sure**:
- ✅ Code is clean and working
- ✅ Documentation is clear and comprehensive
- ✅ Metrics meet or exceed targets
- ✅ Demo is rehearsed and smooth

---

**Good luck! 🚀**
