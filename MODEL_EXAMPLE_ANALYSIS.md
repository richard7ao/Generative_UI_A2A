# Multi-Agent A2A Model Example Analysis

## Source
**Repository:** `maeste/multi-agent-a2a`
**URL:** https://github.com/maeste/multi-agent-a2a

## Key Patterns to Copy

### 1. Host Agent (Orchestrator) Pattern

**Location in Example:** `agents/host_agent/agent.py`

**Pattern:**
```python
class HostAgent(A2ABaseServer):
    """Orchestrates specialized agents based on request analysis."""
    
    def __init__(self, ...):
        # Create AgentCard describing capabilities
        agent_card = AgentCard(
            name="Host Agent",
            description="Orchestrates specialized agents",
            url=f"http://{host}:{port}",
            version="1.0.0",
            capabilities=Capabilities(streaming=True, pushNotifications=True),
            skills=[
                Skill(id="orchestration", name="Agent Orchestration", ...),
                Skill(id="conversation", name="Conversation Management", ...)
            ]
        )
        super().__init__(agent_card=agent_card)
        
        # Store URLs of specialized agents
        self.agent_urls = {
            "data": data_agent_url,
            "planning": planning_agent_url,
            "creative": creative_agent_url
        }
        
        # A2A client for communication
        self.client = A2AClient()
        self.agent_capabilities = {}
    
    async def startup(self):
        """Discover available agents on startup."""
        for agent_type, url in self.agent_urls.items():
            try:
                agent_card = await self.client.discover_agent(url)
                self.agent_capabilities[agent_type] = agent_card
                print(f"Discovered {agent_type} agent at {url}")
            except Exception as e:
                print(f"Error discovering {agent_type} agent: {e}")
    
    async def handle_task(self, task: Task) -> Task:
        """Process user request and delegate to specialized agents."""
        # 1. Extract message text
        message_text = extract_message(task)
        
        # 2. Analyze request to determine which agents to call
        agents_to_call = await self._analyze_request(message_text)
        
        # 3. Call each agent and collect results
        results = []
        for agent_type in agents_to_call:
            if agent_type in self.agent_urls:
                agent_result = await self._call_agent(agent_type, message_text)
                results.append(agent_result)
        
        # 4. Consolidate results into coherent response
        consolidated_result = await self._consolidate_results(message_text, results)
        
        # 5. Update task with results
        task.status.state = TaskState.COMPLETED
        task.status.message = Message(parts=[TextPart(text=consolidated_result)])
        return task
    
    async def _analyze_request(self, message: str) -> List[str]:
        """Determine which agents to call based on keywords."""
        agents = []
        
        # Keyword-based routing
        if any(kw in message.lower() for kw in ["data", "analyze", "statistics"]):
            agents.append("data")
        if any(kw in message.lower() for kw in ["plan", "schedule", "task"]):
            agents.append("planning")
        if any(kw in message.lower() for kw in ["create", "generate", "write"]):
            agents.append("creative")
        
        # Fallback: use all agents if no specific match
        if not agents:
            agents = ["data", "planning", "creative"]
        
        return agents
    
    async def _call_agent(self, agent_type: str, message: str) -> Dict:
        """Call a specialized agent via A2A."""
        agent_url = self.agent_urls.get(agent_type)
        if not agent_url:
            return {"success": False, "response": f"Agent {agent_type} not available"}
        
        try:
            # Send task to agent
            task = await self.client.send_task(agent_url, message)
            
            # Subscribe to task updates (for streaming)
            responses = []
            async for update in self.client.subscribe_to_task(agent_url, task.id):
                responses.append(update)
            
            # Get final result
            final_response = responses[-1] if responses else task
            
            return {
                "agent_type": agent_type,
                "success": final_response.status.state == TaskState.COMPLETED,
                "response": extract_text(final_response),
                "artifacts": final_response.artifacts
            }
        except Exception as e:
            return {
                "agent_type": agent_type,
                "success": False,
                "response": f"Error calling {agent_type} agent: {str(e)}"
            }
    
    async def _consolidate_results(self, original_message: str, results: List[Dict]) -> str:
        """Combine results from multiple agents into coherent response."""
        consolidated_text = "Here's what I found:\n\n"
        
        for result in results:
            agent_type = result.get("agent_type", "unknown")
            success = result.get("success", False)
            response = result.get("response", "No response")
            
            if success:
                consolidated_text += f"**{agent_type.capitalize()} Agent**:\n{response}\n\n"
            else:
                consolidated_text += f"**{agent_type.capitalize()} Agent**: Unable to complete\n\n"
        
        return consolidated_text.strip()
```

**What to Copy for Customer Service:**
- Agent discovery on startup
- Keyword-based intent classification
- Parallel agent calling with result consolidation
- Graceful error handling for unavailable agents

---

### 2. A2A Client Pattern

**Location in Example:** `common/a2a/client.py`

**Pattern:**
```python
class A2AClient:
    """Client for interacting with A2A agents."""
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)
    
    async def discover_agent(self, agent_url: str) -> AgentCard:
        """Fetch agent capabilities from .well-known/agent.json."""
        well_known_url = f"{agent_url.rstrip('/')}/.well-known/agent.json"
        response = await self.http_client.get(well_known_url)
        response.raise_for_status()
        return AgentCard.model_validate(response.json())
    
    async def send_task(self, agent_url: str, text: str) -> Task:
        """Send a new task to an agent."""
        task_id = str(uuid.uuid4())
        message = Message(parts=[TextPart(text=text)])
        status = TaskStatus(state=TaskState.SUBMITTED, message=message)
        task = Task(id=task_id, status=status)
        
        task_url = f"{agent_url.rstrip('/')}/tasks"
        response = await self.http_client.post(
            task_url,
            json=task.model_dump(mode='json')
        )
        response.raise_for_status()
        return Task.model_validate(response.json())
    
    async def get_task(self, agent_url: str, task_id: str) -> Task:
        """Get current status of a task."""
        task_url = f"{agent_url.rstrip('/')}/tasks/{task_id}"
        response = await self.http_client.get(task_url)
        response.raise_for_status()
        return Task.model_validate(response.json())
    
    async def subscribe_to_task(self, agent_url: str, task_id: str) -> AsyncIterator[Task]:
        """Subscribe to real-time updates via WebSocket."""
        ws_url = f"{agent_url.rstrip('/')}/tasks/{task_id}/subscribe".replace("http", "ws")
        async with connect(ws_url) as websocket:
            while True:
                message = await websocket.recv()
                task_update = Task.model_validate(json.loads(message))
                yield task_update
                
                if task_update.status.state in [TaskState.COMPLETED, TaskState.FAILED]:
                    break
```

**What to Copy for Customer Service:**
- Proper task lifecycle management
- Agent discovery with validation
- WebSocket streaming support
- Error handling patterns

---

### 3. A2A Server Base Pattern

**Location in Example:** `common/a2a/server.py`

**Pattern:**
```python
class A2ABaseServer(ABC):
    """Base class for A2A server implementations."""
    
    def __init__(self, agent_card: AgentCard, app: Optional[FastAPI] = None):
        self.agent_card = agent_card
        self.app = app or FastAPI(title=agent_card.name)
        self.tasks: Dict[str, Task] = {}
        self.task_subscribers: Dict[str, Set[WebSocket]] = {}
        self._register_routes()
    
    def _register_routes(self):
        """Register A2A protocol routes."""
        
        # AgentCard discovery
        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            return self.agent_card.model_dump()
        
        # Task creation
        @self.app.post("/tasks")
        async def create_task(task: Dict[str, Any]):
            task_obj = Task.model_validate(task)
            
            # Validate initial state
            if task_obj.status.state != TaskState.SUBMITTED:
                raise HTTPException(status_code=400, detail="New tasks must have 'submitted' state")
            
            # Store and process task
            self.tasks[task_obj.id] = task_obj
            task_obj = await self._update_task_state(task_obj, TaskState.WORKING)
            asyncio.create_task(self._process_task(task_obj))
            
            return task_obj.model_dump()
        
        # Task retrieval
        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str):
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            return self.tasks[task_id].model_dump()
        
        # WebSocket streaming
        @self.app.websocket("/tasks/{task_id}/subscribe")
        async def subscribe_to_task(websocket: WebSocket, task_id: str):
            await websocket.accept()
            if task_id not in self.task_subscribers:
                self.task_subscribers[task_id] = set()
            self.task_subscribers[task_id].add(websocket)
            
            try:
                await websocket.send_text(self.tasks[task_id].model_dump_json())
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.task_subscribers[task_id].discard(websocket)
    
    async def _process_task(self, task: Task):
        """Process task in background with error handling."""
        try:
            result_task = await self.handle_task(task)
            if result_task.status.state not in [TaskState.COMPLETED, TaskState.FAILED]:
                await self._update_task_state(result_task, TaskState.COMPLETED)
        except Exception as e:
            error_message = Message(parts=[TextPart(text=f"Error: {str(e)}")])
            await self._update_task_state(task, TaskState.FAILED, error_message, str(e))
    
    @abstractmethod
    async def handle_task(self, task: Task) -> Task:
        """Process task - implement in subclass."""
        pass
```

**What to Copy for Customer Service:**
- Proper A2A protocol route structure
- Task state management (SUBMITTED → WORKING → COMPLETED)
- WebSocket subscriber management
- Error handling with proper state transitions

---

## How to Apply to Customer Service Project

### Current State
Your project uses ADK's built-in A2A support (`to_a2a()`), which is simpler but less flexible.

### Recommended Iteration

#### Phase 1: Enhance Research Agent Discovery (Quick Win)
Add agent discovery to CS Agent similar to Host Agent pattern:

```python
# In cs_agent/agent.py
class CSAgent:
    async def startup(self):
        """Discover Research Agent on startup."""
        research_url = os.environ.get("RESEARCH_AGENT_URL")
        if research_url:
            try:
                # Discover research agent capabilities
                card = await discover_agent(research_url)
                print(f"Research Agent discovered: {card.name}")
                print(f"Skills: {[s.id for s in card.skills]}")
            except Exception as e:
                print(f"Research Agent unavailable: {e}")
```

#### Phase 2: Better Intent Classification (Medium Impact)
Replace simple prompt-based escalation with keyword-based classification:

```python
# In cs_agent/research_client_tool.py
RESEARCH_KEYWORDS = [
    # Policy analysis
    "conflict", "exception", "edge case", "policy",
    # Deep research
    "compare", "difference", "versus", "all options",
    # Procedures
    "detailed steps", "complete guide", "how exactly",
    # Verification
    "verify", "confirm", "cross-reference"
]

def should_escalate_to_research(query: str) -> bool:
    """Determine if query needs research agent."""
    query_lower = query.lower()
    
    # Check for research keywords
    if any(kw in query_lower for kw in RESEARCH_KEYWORDS):
        return True
    
    # Check query complexity (length, multiple questions)
    if len(query) > 200 or query.count("?") > 1:
        return True
    
    return False
```

#### Phase 3: Task Lifecycle Management (High Impact)
Add proper task tracking to enable better debugging and recovery:

```python
# Add to personal_agent/cs_client_tool.py
class CSTaskManager:
    """Manages tasks sent to CS Agent."""
    
    def __init__(self):
        self.active_tasks: Dict[str, Task] = {}
    
    async def send_message(self, message: str, context_id: str) -> str:
        """Send message and track task."""
        task = await self._create_task(message, context_id)
        self.active_tasks[task.id] = task
        
        # Wait for completion with timeout
        result = await self._wait_for_completion(task.id, timeout=300)
        
        del self.active_tasks[task.id]
        return result
    
    async def _wait_for_completion(self, task_id: str, timeout: float) -> str:
        """Poll for task completion."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task = await self._get_task(task_id)
            if task.status.state == TaskState.COMPLETED:
                return extract_text(task)
            elif task.status.state == TaskState.FAILED:
                raise TaskFailedError(task.status.reason)
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Task {task_id} timed out")
```

---

## Immediate Actions Based on Model

### Action 1: Add Research Agent Discovery
```python
# Add to cs_agent/research_client_tool.py
async def verify_research_agent() -> bool:
    """Verify Research Agent is available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{RESEARCH_AGENT_URL}/.well-known/agent.json"
            )
            if response.status_code == 200:
                card = response.json()
                print(f"Research Agent ready: {card.get('name')}")
                return True
    except Exception as e:
        print(f"Research Agent not available: {e}")
    return False
```

### Action 2: Add Intent Classification
```python
# Add to cs_agent/agent.py
INTENT_PATTERNS = {
    "simple_lookup": ["balance", "status", "what is", "how much"],
    "policy_question": ["policy", "rule", "allowed", "eligible"],
    "procedure": ["how do I", "steps to", "process for"],
    "complex_analysis": ["compare", "conflict", "exception", "all"]
}

def classify_intent(query: str) -> str:
    """Classify user intent to determine agent routing."""
    query_lower = query.lower()
    
    for intent, keywords in INTENT_PATTERNS.items():
        if any(kw in query_lower for kw in keywords):
            return intent
    
    return "general"
```

### Action 3: Add Task Result Consolidation
```python
# Improve CS Agent response synthesis
def synthesize_response(cs_result: str, research_result: str = None) -> str:
    """Combine CS and Research agent results."""
    if not research_result:
        return cs_result
    
    return f"""Based on my analysis:

{cs_result}

Additional research findings:
{research_result}

Is there anything specific about these findings you'd like me to explain further?"""
```

---

## Testing the Model

To test these patterns:

```bash
# 1. Ensure all agents are running
docker compose ps

# 2. Verify research agent discovery
curl http://localhost:9003/.well-known/agent.json

# 3. Test intent classification with different queries
# - Simple: "What's my balance?" → No research
# - Complex: "What are all the exceptions to the overdraft policy?" → Research

# 4. Monitor task lifecycle in logs
docker compose logs -f cs-agent
```

---

## Summary

**Key Insights from Model:**
1. **Agent Discovery** - Don't hardcode, discover at runtime
2. **Intent Classification** - Use keywords to route appropriately
3. **Task Lifecycle** - Proper state management enables debugging
4. **Result Consolidation** - Combine multiple agent outputs coherently
5. **Error Handling** - Graceful degradation when agents unavailable

**What to Implement First:**
1. Add research agent health check (30 min)
2. Implement keyword-based escalation (1 hour)
3. Add task tracking for debugging (1 hour)
4. Improve response synthesis (30 min)
