# A2A Three-Agent Customer Service Architecture

This repository extends the A2A Hackathon Template with a **three-agent system** for customer service:

```
┌─────────────────┐      A2A       ┌──────────────────┐      A2A       ┌─────────────────┐
│  Personal Agent │  ───────────>  │   CS Agent       │  ───────────>  │  Research Agent  │
│    (Port 9001)   │               │   (Port 9002)    │               │   (Port 9003)    │
│                  │               │                  │               │                  │
│ • User's banking │               │ • KB search      │               │ • Deep policy    │
│   assistant      │               │ • Bank tools     │               │   analysis       │
│ • User tools     │               │ • CS tools       │               │ • Cross-doc      │
│ • CS client      │               │ • Research       │               │   synthesis      │
│                  │               │   client         │               │ • Procedure      │
│                  │               │                  │               │   extraction     │
└─────────────────┘               └──────────────────┘               └─────────────────┘
         ^
         │
    Simulated User
   (Test Harness)
```

## Agent Roles

### 1. Personal Agent (`personal_agent/`)
**Port:** 9001

The user's personal banking assistant that serves as the primary interface.

**Capabilities:**
- Acts on user's behalf with user-side banking tools
- Coordinates with Customer Service for bank-side operations
- Handles referrals, card applications, account management
- Maintains conversation context with the user

**Key Files:**
- `agent.py` - Main agent with enhanced user experience prompts
- `cs_client_tool.py` - A2A client for communicating with CS Agent
- `env_toolset.py` - Dynamic environment tool loading

### 2. Customer Service Agent (`cs_agent/`)
**Port:** 9002

The bank's customer service representative with knowledge base access and research support.

**Capabilities:**
- Knowledge base search (BM25 + Vector/RAG)
- Bank-side operations and tools
- Identity verification handling
- Complex query escalation to Research Agent
- Policy interpretation and guidance

**Key Files:**
- `agent.py` - Main agent with RAG + Research Agent integration
- `rag_tools.py` - BM25 and vector search over Redis KB
- `research_client_tool.py` - A2A client for Research Agent
- `env_toolset.py` - Dynamic environment tool loading
- `ingest.py` - KB document indexing at startup

### 3. Research Agent (`research_agent/`)
**Port:** 9003

Specialized deep-research agent for complex policy analysis and cross-document synthesis.

**Capabilities:**
- **Deep Search:** Hybrid BM25 + Vector with reciprocal rank fusion
- **Policy Conflict Analysis:** Identify edge cases, exceptions, and conflicts
- **Procedure Extraction:** Find step-by-step guidance for tasks
- **Related Policy Discovery:** Cross-reference related documents
- **Comprehensive Research:** Answer complex policy questions with full citations

**Key Files:**
- `agent.py` - Main agent with research-focused prompts
- `research_tools.py` - Advanced research tools with fusion search
- `ingest.py` - KB indexing (shared with CS Agent)

## Architecture Benefits

### 1. **Separation of Concerns**
- Personal Agent focuses on user experience and coordination
- CS Agent handles policy queries and bank operations
- Research Agent specializes in deep analysis and synthesis

### 2. **Scalable Knowledge Processing**
- Simple queries handled directly by CS Agent's fast RAG
- Complex queries escalated to Research Agent for thorough analysis
- Prevents token overflow from loading too many documents at once

### 3. **Interoperability**
Each agent can work with other agents in the ecosystem:
- CS Agent can consult Research Agent when available
- Personal Agent can work with any A2A-compatible CS Agent
- Research Agent can support multiple CS Agents

### 4. **Enhanced Capabilities**
The three-agent system can handle:
- Simple account inquiries (Personal → CS)
- Policy questions (Personal → CS → KB)
- Complex scenarios (Personal → CS → Research → KB)
- Conflicting information resolution (CS → Research)
- Multi-document procedural guidance (CS → Research)

## Communication Flow

### Simple Query (Account Balance)
```
User → Personal Agent → CS Agent → [KB Search] → Response
```

### Complex Query (Policy Conflict)
```
User → Personal Agent → CS Agent → Research Agent → [Deep Search]
                                     ↓
                              CS Agent (synthesis) → Response
```

### Multi-Step Process (Dispute Resolution)
```
User → Personal Agent → CS Agent → Research Agent → [Procedure Extraction]
                                     ↓
                              CS Agent → [Bank Tools] → Response
```

## Running the System

### Prerequisites
- Docker and Docker Compose
- Google Cloud Vertex AI API key
- A2A Harness CLI (from a2a-hackathon repo)

### Configuration
Copy `.env.example` to `.env` and set:
```bash
GOOGLE_API_KEY=your_vertex_ai_key
MODEL=gemini-3.5-flash  # Required for hackathon
```

### Start the Agents
```bash
docker compose up --build
```

This starts:
- Personal Agent on port 9001
- CS Agent on port 9002
- Research Agent on port 9003
- Redis on port 6379 (for KB vector search)

### Testing with Harness
```bash
# In the a2a-hackathon repo:
uv run a2a-hack smoke \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002

# Run train tasks
uv run a2a-hack run \
  --personal-url http://localhost:9001 \
  --cs-url http://localhost:9002 \
  --tasks train \
  --save-to results/dev \
  --auto-resume

# View results
uv run tau2 view results/dev
```

## Research Agent Tools

### consult_research_agent(question, context)
Primary tool for comprehensive research. The CS Agent provides:
- `question`: Specific research question
- `context`: Optional customer situation details

### research_policy_conflict(topic)
Analyzes potential conflicts, exceptions, and edge cases in policies.

### research_procedure(task, context)
Extracts step-by-step procedures for specific tasks.

### deep_kb_search(query)
Casts a wide net for extensive document retrieval.

## Design Decisions

1. **Redis Sharing**: CS Agent and Research Agent share the same Redis instance for the knowledge base index, reducing memory footprint while allowing independent scaling.

2. **A2A Communication**: Research Agent communicates over A2A (not function calls), allowing it to potentially run on separate infrastructure or be swapped with other research agents.

3. **Progressive Enhancement**: CS Agent tries simple RAG first, escalating to Research Agent only when needed - optimizing for latency on common queries.

4. **Tool Specialization**: Each agent's tools are tailored to its role:
   - Personal Agent: User tools + CS client
   - CS Agent: KB search + Bank tools + Research client
   - Research Agent: Deep analysis tools only

## Hackathon Judging Criteria

This architecture addresses the A2A track's judging criteria:

1. **Agents Working Together**: Clear separation with defined A2A communication patterns
2. **Interoperability**: Each agent follows A2A protocol and can work with other compatible agents
3. **Extensibility**: New agents can be added (e.g., fraud detection, loan specialist) following the same pattern

## Files Changed from Template

### New Files
- `research_agent/` - Entire research agent service
- `cs_agent/research_client_tool.py` - A2A client for research agent

### Modified Files
- `docker-compose.yml` - Added research-agent service
- `.env.example` - Added RESEARCH_AGENT_URL
- `cs_agent/agent.py` - Added research tools and guidance
- `personal_agent/agent.py` - Enhanced prompts for UX

## Future Enhancements

Potential improvements for production:
1. **Caching Layer**: Cache research results for common queries
2. **Async Research**: Background research for anticipated questions
3. **Research Summaries**: Pre-computed policy summaries for common topics
4. **Feedback Loop**: CS Agent learns when to escalate based on success metrics
5. **Multi-Research**: Parallel research queries for complex multi-part questions
