"""Tool that lets the CS agent talk to the research agent over A2A.

The research agent provides deep policy research and analysis capabilities
to help the CS agent answer complex questions and resolve ambiguous scenarios.

Based on patterns from: https://github.com/maeste/multi-agent-a2a
"""

import os
import uuid
from typing import Optional

import httpx
from a2a.client import ClientConfig, ClientFactory, minimal_agent_card
from a2a.types import Message, Part, Role, Task, TextPart
from google.adk.tools import ToolContext

from env_toolset import session_id
from circuit_breaker import get_circuit_breaker, CircuitBreaker

RESEARCH_AGENT_URL = os.environ.get("RESEARCH_AGENT_URL", "http://host.docker.internal:8090/research-agent")

_TIMEOUT_S = 300.0

# Intent classification patterns (from model example)
RESEARCH_KEYWORDS = [
    # Policy analysis
    "conflict", "exception", "edge case", "all policies", "policy comparison",
    # Deep research
    "compare", "difference", "versus", "vs", "detailed analysis",
    # Procedures
    "complete steps", "detailed procedure", "full process", "exactly how",
    # Verification
    "cross-reference", "verify against", "confirm with multiple sources",
    # Complexity indicators
    "multiple accounts", "different scenarios", "various cases",
]

SIMPLE_QUERY_PATTERNS = [
    # Direct lookups
    "what is my", "show me", "get my", "current balance", "account status",
    # Simple questions
    "how much", "when", "where", "what time", "is it open",
    # Status checks
    "is this active", "status of", "check if",
]

# Track research agent availability
_research_agent_available: Optional[bool] = None
_research_agent_capabilities: Optional[dict] = None


def _text_of_message(message: Message) -> str:
    texts = []
    for part in message.parts or []:
        root = getattr(part, "root", part)
        if isinstance(root, TextPart) and root.text:
            texts.append(root.text)
    return "\n".join(texts)


def _text_of_task(task: Task) -> str:
    texts = []
    for artifact in task.artifacts or []:
        for part in artifact.parts or []:
            root = getattr(part, "root", part)
            if isinstance(root, TextPart) and root.text:
                texts.append(root.text)
    if task.status is not None and task.status.message is not None:
        text = _text_of_message(task.status.message)
        if text:
            texts.append(text)
    return "\n".join(texts)


# ============================================================================
# Agent Discovery & Health Check (from model example)
# ============================================================================

async def discover_research_agent() -> Optional[dict]:
    """Discover research agent capabilities from its AgentCard.
    
    Returns:
        AgentCard as dict if available, None otherwise.
    """
    global _research_agent_available, _research_agent_capabilities
    
    # Return cached result if available
    if _research_agent_available is not None:
        return _research_agent_capabilities if _research_agent_available else None
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            well_known_url = f"{RESEARCH_AGENT_URL.rstrip('/')}/.well-known/agent.json"
            response = await client.get(well_known_url)
            
            if response.status_code == 200:
                card = response.json()
                _research_agent_available = True
                _research_agent_capabilities = card
                print(f"[CS Agent] Research Agent discovered: {card.get('name')}")
                print(f"[CS Agent] Skills: {[s.get('id') for s in card.get('skills', [])]}")
                return card
            else:
                print(f"[CS Agent] Research Agent not available: HTTP {response.status_code}")
                _research_agent_available = False
                return None
                
    except Exception as e:
        print(f"[CS Agent] Research Agent discovery failed: {e}")
        _research_agent_available = False
        return None


def is_research_agent_available() -> bool:
    """Check if research agent is available (uses cached discovery result)."""
    return _research_agent_available if _research_agent_available is not None else True


# ============================================================================
# Intent Classification (from model example)
# ============================================================================

def classify_research_intent(query: str) -> dict:
    """Classify whether a query needs deep research.
    
    Based on keyword patterns from the multi-agent-a2a model example.
    
    Args:
        query: The user's question or request.
        
    Returns:
        Dict with classification results:
        - needs_research: bool
        - confidence: str ('high', 'medium', 'low')
        - reason: str explaining the classification
        - suggested_approach: str
    """
    query_lower = query.lower()
    
    # Check for simple query patterns (definitely don't need research)
    for pattern in SIMPLE_QUERY_PATTERNS:
        if pattern in query_lower:
            return {
                "needs_research": False,
                "confidence": "high",
                "reason": f"Simple query pattern detected: '{pattern}'",
                "suggested_approach": "Use direct KB search or environment tools"
            }
    
    # Check for research keywords
    matched_keywords = []
    for keyword in RESEARCH_KEYWORDS:
        if keyword in query_lower:
            matched_keywords.append(keyword)
    
    # Check complexity indicators
    word_count = len(query.split())
    question_count = query.count("?")
    
    if matched_keywords:
        confidence = "high" if len(matched_keywords) >= 2 else "medium"
        return {
            "needs_research": True,
            "confidence": confidence,
            "reason": f"Research keywords detected: {matched_keywords}",
            "suggested_approach": "Escalate to Research Agent for deep analysis"
        }
    
    # Check for complexity without keywords
    if word_count > 50 or question_count > 1:
        return {
            "needs_research": True,
            "confidence": "medium",
            "reason": f"Complex query (words: {word_count}, questions: {question_count})",
            "suggested_approach": "Consider research if initial KB search fails"
        }
    
    # Default: simple query
    return {
        "needs_research": False,
        "confidence": "low",
        "reason": "No research indicators detected",
        "suggested_approach": "Start with KB search, escalate if unclear"
    }


# ============================================================================
# Smart Research Consultation (enhanced with model patterns)
# ============================================================================

async def smart_consult_research(
    question: str,
    context: str = "",
    previous_results: list = None,
    tool_context: ToolContext = None,
) -> dict:
    """Smart research consultation with intent classification.
    
    This is an enhanced version that uses intent classification to decide
    whether research is actually needed, and provides detailed metadata
    for better debugging and optimization.
    
    Args:
        question: The research question.
        context: Optional customer context.
        previous_results: Results from previous KB searches (if failed/unclear).
        tool_context: ADK tool context.
        
    Returns:
        Dict with:
        - result: str the research findings
        - classification: dict intent classification
        - used_research: bool whether research agent was called
        - fallback_reason: str if research wasn't used
    """
    # Classify intent
    classification = classify_research_intent(question)
    
    # Check if research agent is available
    if not is_research_agent_available():
        # Try to discover it
        card = await discover_research_agent()
        if not card:
            return {
                "result": "Research Agent not available. Please try a simpler query or contact support.",
                "classification": classification,
                "used_research": False,
                "fallback_reason": "Research Agent unavailable"
            }
    
    # Decision: use research or not
    if not classification["needs_research"]:
        # For low-confidence simple queries, we could skip research
        # But for now, still call it if explicitly requested
        pass  # Continue to research
    
    # Call research agent
    research_result = await consult_research_agent(question, context, tool_context)
    
    return {
        "result": research_result,
        "classification": classification,
        "used_research": True,
        "fallback_reason": None
    }


async def consult_research_agent(
    question: str,
    context: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Consult the research agent for deep policy research and analysis.

    Use this tool when:
    - The user's question requires deep policy analysis
    - You need to cross-reference multiple knowledge base documents
    - You're unsure about conflicting policies or edge cases
    - You need detailed procedural guidance
    - Standard KB searches haven't provided a clear answer

    Args:
        question: The research question or policy query. Be specific about what
            you need to know.
        context: Optional context about the customer situation or scenario.
            Include relevant customer details, account type, or specific
            circumstances that might affect the answer.

    Returns:
        Comprehensive research findings from the knowledge base, including
        relevant documents, analysis, and recommendations.
    """
    # Check circuit breaker
    circuit = get_circuit_breaker()
    if not circuit.can_execute():
        cb_state = circuit.get_state()
        return (
            f"[Research Agent temporarily unavailable - Circuit {cb_state['state']}. "
            f"Last failure: {cb_state['failure_count']} consecutive failures. "
            f"Using direct KB search instead.]"
        )
    
    # Build the research query with context if provided
    full_query = question
    if context:
        full_query = f"Question: {question}\n\nContext: {context}"

    outgoing = Message(
        message_id=uuid.uuid4().hex,
        role=Role.user,
        parts=[Part(root=TextPart(text=full_query))],
        context_id=session_id(tool_context),
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as http_client:
            client = ClientFactory(
                ClientConfig(streaming=False, httpx_client=http_client)
            ).create(minimal_agent_card(RESEARCH_AGENT_URL, ["JSONRPC"]))

            reply = ""
            async for event in client.send_message(outgoing):
                if isinstance(event, Message):
                    reply = _text_of_message(event) or reply
                elif isinstance(event, tuple) and isinstance(event[0], Task):
                    reply = _text_of_task(event[0]) or reply
        
        # Record success
        circuit.record_success()
        return reply or "[no response from research agent]"
        
    except Exception as e:
        # Record failure
        circuit.record_failure()
        print(f"[Research Client] Error calling research agent: {e}")
        return f"[Research Agent error: {type(e).__name__}. Circuit state: {circuit.get_state()['state']}. Consider using direct KB search.]"


# Convenience wrappers for common research patterns


async def research_policy_conflict(
    topic: str,
    tool_context: ToolContext = None,
) -> str:
    """Research potential policy conflicts or edge cases.

    Args:
        topic: The policy area to analyze for conflicts.

    Returns:
        Analysis of potential conflicts, exceptions, or edge cases.
    """
    question = f"Analyze policy conflicts, exceptions, and edge cases related to: {topic}"
    return await consult_research_agent(question, "", tool_context)


async def research_procedure(
    task: str,
    context: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Research step-by-step procedures for a specific task.

    Args:
        task: Description of the task or process.
        context: Optional context about the situation.

    Returns:
        Detailed procedural guidance with steps and requirements.
    """
    question = f"Extract complete step-by-step procedures for: {task}"
    return await consult_research_agent(question, context, tool_context)


async def deep_kb_search(
    query: str,
    tool_context: ToolContext = None,
) -> str:
    """Perform a deep search of the knowledge base.

    Args:
        query: The search query - keywords or natural language question.

    Returns:
        Comprehensive search results from multiple strategies.
    """
    return await consult_research_agent(
        f"Deep research search for: {query}",
        "",
        tool_context,
    )
