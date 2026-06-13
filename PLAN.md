# A2A Hackathon - Detailed Planning & Strategy

## 1. Testing Strategy & Validation Plan

### Phase 1: Local Smoke Testing (Immediate)
```bash
# Test individual agent health
curl http://localhost:9001/.well-known/agent.json  # Personal Agent
curl http://localhost:9002/.well-known/agent.json  # CS Agent  
curl http://localhost:9003/.well-known/agent.json  # Research Agent

# Full smoke test with harness
uv run a2a-hack smoke \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002
```

**What to verify:**
- [ ] All three agents serve agent cards correctly
- [ ] contextId propagation works (user→personal→CS→research)
- [ ] No 5-minute timeout errors
- [ ] Redis connection stable
- [ ] KB index loads without errors

### Phase 2: Train Split Analysis (Day 1-2)
```bash
# Run train split
uv run a2a-hack run \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002 \
  --tasks train \
  --save-to results/train-v1 \
  --auto-resume

# Analyze failures
uv run tau2 view results/train-v1
```

**Analysis Checklist:**
- [ ] Categorize failures by agent (personal vs CS vs research)
- [ ] Identify patterns in failed tasks
- [ ] Check for contextId errors (critical!)
- [ ] Look for timeout issues
- [ ] Flag hallucination/invention of facts
- [ ] Check tool calling errors

### Phase 3: Research Agent Efficacy Testing

**Test Scenarios:**

| Scenario | Expected Behavior | Validation |
|----------|------------------|------------|
| Simple balance query | CS Agent handles directly, no research | Check logs for research calls |
| Complex policy conflict | CS → Research → Synthesis | Verify research is consulted |
| Multi-step procedure | Research extracts steps | Check procedure completeness |
| Ambiguous scenario | Research finds edge cases | Verify conflict detection |
| Unknown query | Escalate appropriately | Check graceful fallback |

**Metrics to Track:**
- Research agent call frequency (% of CS queries)
- Average research response time
- CS agent's ability to synthesize research results
- False positives (research called when not needed)
- False negatives (research NOT called when needed)

---

## 2. Prompt Engineering Iteration Framework

### Iteration Cycle (Every 2-3 Hours)

```
Run Tests → Analyze Failures → Hypothesize → Prompt Change → Validate → Document
```

### Personal Agent Prompt Experiments

**Current Focus Areas:**
1. **User clarification flow** - When to ask vs when to act
2. **CS handoff criteria** - Clearer rules for escalation
3. **Tool argument handling** - Preventing placeholder values
4. **Response conciseness** - Avoiding over-explanation

**Test Variants:**
- [ ] Add explicit "when to ask user" examples
- [ ] Strengthen identity verification relay instructions
- [ ] Add "never invent" repetition in key sections
- [ ] Test different conversation flow structures

### CS Agent Prompt Experiments

**Current Focus Areas:**
1. **Research escalation criteria** - When to call research agent
2. **KB search strategy** - BM25 vs Vector selection guidance
3. **Tool result synthesis** - Converting tool output to user-friendly responses
4. **Verification handling** - Managing the 2-of-4 verification rule

**Test Variants:**
- [ ] Add specific examples of "call research when..."
- [ ] Include decision tree for KB search selection
- [ ] Strengthen "search before you act" reminder
- [ ] Add verification flow template

### Research Agent Prompt Experiments

**Current Focus Areas:**
1. **Citation quality** - Ensuring sources are clearly referenced
2. **Synthesis clarity** - Converting multiple docs into actionable guidance
3. **Confidence signaling** - When to be certain vs uncertain
4. **Format consistency** - Structured response format adherence

**Test Variants:**
- [ ] Require explicit document IDs in citations
- [ ] Add "if inconclusive" handling instructions
- [ ] Test different response structure formats
- [ ] Strengthen conflict flagging instructions

### Prompt Versioning Strategy

```
prompts/
  personal-agent/
    v1-base.md
    v2-clarification.md
    v3-concise.md
  cs-agent/
    v1-base.md
    v2-research-criteria.md
    v3-synthesis.md
  research-agent/
    v1-base.md
    v2-citations.md
    v3-confidence.md
```

---

## 3. Error Handling & Edge Case Coverage

### Critical Error Categories

#### A. contextId Errors (DISQUALIFYING!)
**Root Causes:**
- Not propagating contextId to env tool calls
- Not propagating contextId to A2A messages
- Generating new contextId mid-conversation

**Detection:**
```bash
# Look for these in logs:
# - "contextId mismatch"
# - "session not found"
# - Different IDs in chained calls
```

**Prevention:**
- [ ] Audit `env_toolset.py` session_id usage
- [ ] Audit `cs_client_tool.py` context_id propagation
- [ ] Audit `research_client_tool.py` context_id propagation
- [ ] Add runtime contextId validation

#### B. Timeout Errors (SCORE = 0)
**Root Causes:**
- Research agent taking too long on complex queries
- Infinite loops in agent reasoning
- Rate limiting from Vertex AI

**Mitigation:**
- [ ] Add timeout warning at 4 minutes
- [ ] Implement research result caching
- [ ] Limit research search depth for simple queries
- [ ] Add circuit breaker for research agent failures

#### C. Tool Calling Errors
**Patterns:**
- Wrong tool name
- Invalid JSON arguments
- Missing required parameters
- Hallucinated tools

**Mitigation:**
- [ ] Strengthen tool descriptions
- [ ] Add argument validation in tool wrappers
- [ ] Log all tool calls for analysis

#### D. Knowledge Gaps
**Patterns:**
- KB search returns no results
- Research agent finds no relevant docs
- Conflicting information in KB

**Mitigation:**
- [ ] Add fallback search strategies
- [ ] Improve query expansion
- [ ] Document KB coverage gaps

### Edge Case Scenarios to Test

1. **Empty search results** - How does CS agent respond?
2. **Conflicting KB documents** - Does research agent flag it?
3. **Research agent timeout** - Does CS agent fallback gracefully?
4. **User refuses verification** - Proper handling?
5. **Circular tool calls** - Prevention mechanism?
6. **Very long user messages** - Truncation handling?
7. **Special characters in queries** - Escaping handled?
8. **Redis connection failure** - Graceful degradation?

---

## 4. Competition Scoring Optimization

### Scoring Breakdown
- 50%: How well YOUR agents work together
- 50%: How well YOUR agents work with OTHER teams' agents

### Strategy A: Maximize Internal Cohesion (50%)

**Focus:** Personal ↔ CS ↔ Research seamless operation

**Tactics:**
1. **Conservative research escalation** - Don't call research for simple queries (latency)
2. **Clear handoff protocols** - Well-defined when to escalate
3. **Error recovery** - If research fails, CS should still respond
4. **Consistent tone** - All agents sound like part of same bank

**Metrics to Optimize:**
- End-to-end success rate on train tasks
- Average response time
- Error recovery rate

### Strategy B: Maximize Interoperability (50%)

**Focus:** Work with unknown Personal Agents and unknown CS Agents

**Tactics:**
1. **Strict A2A compliance** - Follow protocol exactly
2. **Defensive programming** - Handle malformed messages gracefully
3. **Clear documentation** - Other teams can understand our interface
4. **Flexible input handling** - Accept various message formats

**Key Implementation Details:**
- Agent card must be perfectly formatted
- Handle both Message and Task responses
- Accept streaming off (as per template default)
- Graceful degradation if research agent unavailable

### Competitive Differentiation

**Our Unique Advantages:**
1. **Research Agent** - Most teams will only have 2 agents
2. **Progressive Escalation** - Smart routing of queries
3. **Hybrid Search** - BM25 + Vector fusion in research
4. **Conflict Detection** - Explicit policy conflict analysis

**Risk Mitigation:**
- Research agent could add latency - optimize query routing
- Three agents = more failure points - add health checks
- Complexity = harder to debug - add comprehensive logging

---

## 5. Interoperability Testing Checklist

### A2A Protocol Compliance

**Agent Card Requirements:**
- [ ] Valid JSON at `/.well-known/agent.json`
- [ ] Required fields: name, description, url, version, capabilities, skills
- [ ] skills array with id, name, description
- [ ] Correct protocolVersion

**Message Handling:**
- [ ] Accept `message/send` with text parts
- [ ] Handle `contextId` in incoming messages
- [ ] Return `Task` or `Message` response
- [ ] Support non-streaming (streaming off)
- [ ] Read reply from `artifacts[].parts[].text` or `status.message.parts[].text`

**Session Management:**
- [ ] Use `contextId` as session key
- [ ] Isolate conversations by contextId
- [ ] Don't persist state across contextIds

### External Agent Testing

**Test with Mock External Agents:**

```python
# Mock personal agent that sends unexpected formats
# Mock CS agent with different response patterns
# Test our agents' robustness
```

**Scenarios:**
- [ ] External agent sends malformed JSON
- [ ] External agent omits contextId
- [ ] External agent uses unexpected response format
- [ ] External agent is slow to respond
- [ ] External agent returns empty response

---

## 6. Research Agent Refinement Strategies

### Option A: Query Classification (Recommended)
Add a lightweight classifier to route queries:

```python
# In CS Agent
async def should_escalate_to_research(query: str, context: dict) -> bool:
    """
    Classify if query needs deep research.
    
    Escalate if:
    - Query mentions conflicts, exceptions, edge cases
    - Multiple policy areas referenced
    - Previous KB search was inconclusive
    - Query explicitly asks for "all" or "every" option
    
    Don't escalate if:
    - Simple factual lookup
    - Single account action
    - Already answered in conversation history
    """
```

### Option B: Caching Layer
Cache research results for common queries:

```python
# Redis cache for research results
# Key: hash of (question + context fingerprint)
# TTL: 1 hour for dynamic content
```

### Option C: Parallel Research
For complex multi-part questions:

```python
# Break question into sub-queries
# Run research in parallel
# Synthesize results
```

### Option D: Research Feedback Loop
Track which research calls led to successful resolutions:

```python
# Log: query → research_called → outcome
# Learn patterns over time
# Adjust escalation criteria
```

### Current Research Agent Tuning

**Parameter Exploration:**

| Parameter | Current | Test Values | Impact |
|-----------|---------|-------------|--------|
| top_k (deep_search) | 10 | 5, 8, 15 | Recall vs precision |
| top_k (procedure) | 8 | 5, 10, 12 | Completeness |
| RRF k constant | 60 | 40, 80 | Ranking quality |
| Embedding batch | 25 | 10, 50 | Index build time |

---

## 7. Logging & Debugging Infrastructure

### Structured Logging

Add to all agents:
```python
import logging
import json
from datetime import datetime

class AgentLogger:
    def log_decision(self, agent: str, decision: str, context: dict):
        """Log agent decisions for analysis."""
        pass
    
    def log_tool_call(self, agent: str, tool: str, args: dict, result: dict):
        """Log tool calls with context."""
        pass
    
    def log_a2a_message(self, direction: str, from_agent: str, to_agent: str, 
                        context_id: str, content_preview: str):
        """Log A2A communication."""
        pass
```

### Debug Endpoints (Development Only)

```python
# Add to main.py for debugging
@app.get("/debug/session/{context_id}")
async def debug_session(context_id: str):
    """Return session state for debugging."""
    pass

@app.get("/debug/kb/search")
async def debug_kb_search(query: str):
    """Direct KB search for testing."""
    pass
```

### Conversation Tracing

```python
# Generate conversation flow diagrams
# Input: conversation log
# Output: sequence diagram (PlantUML or Mermaid)
```

---

## 8. Submission Checklist & Validation

### Pre-Submission Validation

**Code Requirements:**
- [ ] Uses `gemini-3.5-flash` (no other models)
- [ ] A2A protocol compliant
- [ ] contextId discipline maintained
- [ ] Statelessness across contextIds
- [ ] Under 5 min per turn, 10 min per task

**File Requirements:**
- [ ] Public GitHub repo
- [ ] `.env` with working API key (for marking)
- [ ] `docker-compose.yml` follows template shape
- [ ] All agents in designated ports (9001, 9002, 9003)
- [ ] README with setup instructions

**Testing Requirements:**
- [ ] `a2a-hack smoke` passes
- [ ] Train split run completed
- [ ] No contextId errors in logs
- [ ] No timeout errors

### Submission Day Plan

**T-2 Hours:**
- [ ] Final smoke test
- [ ] Verify all files committed
- [ ] Verify `.env` has valid key
- [ ] Create submission tag: `git tag -a v1.0 -m "Hackathon submission"`

**T-1 Hour:**
- [ ] Test on clean machine (if possible)
- [ ] Verify docker build from scratch
- [ ] Check README accuracy

**T-30 Minutes:**
- [ ] Submit repo URL at hackathon.a2anet.com
- [ ] Verify submission confirmation
- [ ] Prepare presentation (if invited to stage)

### Presentation Prep (If Selected)

**Key Points to Highlight:**
1. Three-agent architecture rationale
2. Research agent's unique capabilities
3. Progressive escalation strategy
4. Interoperability design
5. Key learnings from iteration

**Demo Flow:**
1. Show simple query (fast path)
2. Show complex query (research escalation)
3. Show error recovery
4. Show interoperability with another team

---

## 9. Time Allocation Plan

### Day 1 (Today) - Foundation
- [x] 3-agent architecture built (DONE)
- [ ] 2 hours: Smoke testing and fix critical bugs
- [ ] 2 hours: Run train split, categorize failures
- [ ] 2 hours: First prompt iteration based on failures

### Day 2 - Optimization
- [ ] 3 hours: Research agent efficacy testing and tuning
- [ ] 2 hours: Prompt engineering iteration
- [ ] 2 hours: Edge case handling
- [ ] 1 hour: Interoperability testing

### Day 3 - Hardening
- [ ] 2 hours: Performance optimization
- [ ] 2 hours: Error recovery improvements
- [ ] 2 hours: Final prompt tuning
- [ ] 2 hours: Documentation and cleanup

### Day 4 - Submission
- [ ] 2 hours: Final testing
- [ ] 1 hour: Submission
- [ ] 1 hour: Presentation prep (if needed)

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Research agent timeouts | Medium | High | Add circuit breaker, fallback to CS only |
| contextId bugs | Low | Critical | Multiple audits, smoke test validation |
| Rate limiting (429s) | Medium | Medium | Reduce concurrency, add retries |
| KB search quality poor | Medium | High | Tune search, add synonyms |
| Other teams' agents fail | High | Medium | Defensive programming, graceful degradation |
| Docker build issues | Low | Medium | Test builds early, minimal dependencies |
| Research adds too much latency | Medium | High | Smart routing, don't call for simple queries |

---

## Next Actions (Priority Order)

1. **Run smoke test** - Verify 3-agent system works
2. **Run train split** - Get baseline failure analysis
3. **Fix any critical bugs** - contextId, timeouts, crashes
4. **First prompt iteration** - Based on top 3 failure patterns
5. **Research agent tuning** - Optimize escalation criteria
6. **Edge case testing** - Empty results, conflicts, timeouts

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Day 1 | 3-agent architecture | Better specialization, higher interoperability score |
| Day 1 | Research as separate agent | Can be replaced/swapped, follows A2A protocol |
| Day 1 | Shared Redis | Reduces memory, faster startup |
| Day 1 | Progressive escalation | Latency optimization for simple queries |
