# Immediate Next Actions (Priority Order)

## Action 1: Smoke Test (30 minutes)
**Goal:** Verify all three agents start and communicate correctly.

```bash
# 1. Start the system
cd /Users/richardlao/CascadeProjects/a2a-customer-service-agents
docker compose up --build

# 2. In another terminal, verify agent cards
curl http://localhost:9001/.well-known/agent.json
curl http://localhost:9002/.well-known/agent.json  
curl http://localhost:9003/.well-known/agent.json

# 3. Run harness smoke test (requires a2a-hackathon repo)
cd /path/to/a2a-hackathon
uv run a2a-hack smoke \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002
```

**Success Criteria:**
- All 3 agents return valid agent cards
- Smoke test shows conversation flow
- No contextId errors in output
- No timeout errors

**If Failures:**
- Check `docker compose logs` for startup errors
- Verify Redis is healthy: `docker compose ps`
- Check for port conflicts: `lsof -i :9001,9002,9003`

---

## Action 2: Run Train Split (1-2 hours)
**Goal:** Get baseline performance metrics and identify failure patterns.

```bash
# Run train tasks
cd /path/to/a2a-hackathon
uv run a2a-hack run \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002 \
  --tasks train \
  --save-to results/train-v1 \
  --auto-resume

# Analyze results
uv run tau2 view results/train-v1
```

**What to Capture:**
- Overall success rate
- Top 5 failure categories
- Average completion time
- Any contextId errors (CRITICAL!)
- Tasks where research agent was/wasn't called

**Document in:** `results/train-v1-analysis.md`

---

## Action 3: Quick Fix Iteration (2-3 hours)
**Goal:** Fix the top 3 failure patterns from train split.

**Decision Framework:**
1. If contextId errors → DEBUG IMMEDIATELY (disqualifying)
2. If timeout errors → Optimize research agent escalation
3. If KB search failures → Tune search queries
4. If tool calling errors → Improve prompt/tool descriptions

**Process:**
1. Pick top failure pattern
2. Examine conversation logs
3. Hypothesize root cause
4. Make targeted fix
5. Re-run smoke test
6. Re-run 5-10 failed tasks to verify fix

---

## Action 4: Research Agent Tuning (2 hours)
**Goal:** Optimize when research agent is called.

**Current Escalation Logic:** CS Agent decides based on prompt guidance.

**Experiments to Try:**

### Option A: Add Explicit Examples
Add to CS Agent prompt:
```
EXAMPLES OF WHEN TO CALL RESEARCH:
- User asks: "What are all the exceptions to the overdraft policy?"
  → CALL research_policy_conflict("overdraft policy")
  
- User asks: "How do I dispute a transaction?"
  → First try kb_search_vector, if unclear → CALL research_procedure("dispute transaction")

EXAMPLES OF WHEN NOT TO CALL RESEARCH:
- User asks: "What's my account balance?"
  → Use env tools directly, NO research needed

- User asks: "What are your hours?"
  → Use kb_search_bm25, NO research needed
```

### Option B: Add Simple Classifier
Create `cs_agent/query_classifier.py`:
```python
def needs_research(query: str, previous_results: list) -> bool:
    """Quick heuristic classifier."""
    research_keywords = [
        "conflict", "exception", "edge case", "all policies",
        "compare", "difference between", "vs", "versus",
        "detailed steps", "complete procedure"
    ]
    
    # Check for research keywords
    if any(kw in query.lower() for kw in research_keywords):
        return True
    
    # Check if previous searches failed
    if not previous_results:
        return True
    
    return False
```

---

## Action 5: Interoperability Check (1 hour)
**Goal:** Verify our agents work with standard A2A clients.

```bash
# Test that our agents accept standard A2A message format
# (This simulates what other teams' agents will send)

# Send test message to personal agent
curl -X POST http://localhost:9001 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "What is my account balance?"}]
      },
      "contextId": "test-session-123"
    },
    "id": 1
  }'

# Expected: Valid JSON response with Task or Message
```

**Also Verify:**
- [ ] Agent card is valid JSON
- [ ] Agent card has all required fields
- [ ] Handles streaming off correctly
- [ ] Returns text in expected locations

---

## Today's Focus (First 6 Hours)

| Time | Action | Success Metric |
|------|--------|----------------|
| 0:00-0:30 | Smoke test | All 3 agents healthy |
| 0:30-2:30 | Train split run | Have results to analyze |
| 2:30-3:00 | Analyze failures | Top 3 patterns identified |
| 3:00-5:00 | Fix top issues | 50% of top failures resolved |
| 5:00-6:00 | Re-run smoke | No regressions |

**Stop Criteria for the Day:**
- Smoke test passes consistently
- No contextId errors anywhere
- Train split success rate > 60%
- Research agent is being called appropriately (not too much, not too little)

---

## Research Agent Specific Tuning

### Check If Research Is Being Called Correctly

Add temporary logging to `cs_agent/research_client_tool.py`:
```python
async def consult_research_agent(...):
    print(f"[RESEARCH CALL] Question: {question[:50]}... Context: {context[:50]}...")
    # ... rest of function
```

Then analyze:
- How many queries trigger research?
- What's the average research time?
- Are simple queries being escalated unnecessarily?
- Are complex queries being missed?

### Tune Escalation Threshold

If research is called too often (adds latency):
- Strengthen "try KB search first" guidance
- Add "only call research if" conditions

If research is not called enough (poor answers):
- Add "call research when uncertain"
- Lower threshold for complex queries

---

## Quick Debugging Commands

```bash
# Watch all logs
docker compose logs -f

# Watch specific agent
docker compose logs -f cs-agent

# Check Redis
docker compose exec redis redis-cli ping

# Check KB index
docker compose exec redis redis-cli FT.INFO kb_idx

# Restart single agent
docker compose restart cs-agent

# Clean slate
docker compose down -v
docker compose up --build
```

---

## Questions to Answer Today

1. **Does the 3-agent system start cleanly?**
2. **What % of train tasks succeed?**
3. **What's the #1 failure pattern?**
4. **Is research being called appropriately?**
5. **Are there any contextId errors?**

Answer these = solid foundation for iteration tomorrow.
