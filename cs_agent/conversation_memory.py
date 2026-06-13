"""Conversation memory management for multi-turn context preservation.

Based on Advanced Strategy #2: Conversation Memory Management
Summarizes key facts to preserve context across long conversations.
"""

import os
import time
from typing import Dict, List, Optional

from google import genai
from google.genai import types

MODEL = os.environ.get("MODEL", "gemini-3.5-flash")


class ConversationMemory:
    """Manages conversation context and key fact extraction."""
    
    def __init__(self, max_history: int = 10):
        """Initialize memory.
        
        Args:
            max_history: Maximum number of turns to keep in raw history
        """
        self.max_history = max_history
        self.raw_history: List[Dict] = []
        self.key_facts: Dict[str, any] = {}
        self.summary: str = ""
        self.last_summary_time: float = 0
        self.summary_interval: float = 300  # 5 minutes
    
    def add_turn(self, role: str, message: str, tools_used: List[str] = None):
        """Add a conversation turn.
        
        Args:
            role: "user" or "assistant"
            message: The message content
            tools_used: List of tools used in this turn
        """
        turn = {
            "role": role,
            "message": message,
            "tools_used": tools_used or [],
            "timestamp": time.time()
        }
        
        self.raw_history.append(turn)
        
        # Trim history if too long
        if len(self.raw_history) > self.max_history:
            # Trigger summarization before trimming
            if time.time() - self.last_summary_time > self.summary_interval:
                self._update_summary()
            self.raw_history = self.raw_history[-self.max_history:]
        
        # Extract key facts from user messages
        if role == "user":
            self._extract_facts(message)
    
    def _extract_facts(self, message: str):
        """Extract key facts from user message.
        
        Uses simple heuristics for common patterns:
        - Account numbers
        - Phone numbers
        - Email addresses
        - Dates
        - Amounts
        """
        import re
        
        # Account numbers (masked)
        account_patterns = [
            r'account\s*(?:number)?[:\s]*(\d{4,})',
            r'acct[:\s]*(\d{4,})',
        ]
        for pattern in account_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                self.key_facts["account_referenced"] = matches[0]
        
        # Phone numbers
        phone_pattern = r'(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
        phones = re.findall(phone_pattern, message)
        if phones:
            self.key_facts["phone_mentioned"] = phones[0]
        
        # Email addresses
        email_pattern = r'[\w.-]+@[\w.-]+\.\w+'
        emails = re.findall(email_pattern, message)
        if emails:
            self.key_facts["email_mentioned"] = emails[0]
        
        # Dates
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        ]
        for pattern in date_patterns:
            dates = re.findall(pattern, message)
            if dates:
                self.key_facts["date_mentioned"] = dates[0]
        
        # Dollar amounts
        amount_pattern = r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        amounts = re.findall(amount_pattern, message)
        if amounts:
            self.key_facts["amount_mentioned"] = amounts[0]
    
    async def _update_summary(self):
        """Generate conversation summary using LLM."""
        if len(self.raw_history) < 3:
            return
        
        # Build conversation text
        conversation_text = "\n".join([
            f"{turn['role'].upper()}: {turn['message'][:200]}"
            for turn in self.raw_history
        ])
        
        summary_prompt = f"""Summarize the key facts from this conversation:

CONVERSATION:
{conversation_text}

Extract:
1. User's identity details mentioned (if any)
2. Account types or numbers referenced
3. Issues being resolved
4. Actions already taken
5. Outstanding questions or needs

Keep under 150 words. Be factual and specific."""
        
        try:
            client = genai.Client()
            response = client.models.generate_content(
                model=MODEL,
                contents=summary_prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            
            self.summary = response.text.strip()
            self.last_summary_time = time.time()
            
        except Exception as e:
            print(f"[ConversationMemory] Summary error: {e}")
    
    def get_context(self) -> str:
        """Get current conversation context for agent.
        
        Returns:
            Formatted context string
        """
        parts = []
        
        # Add summary if available
        if self.summary:
            parts.append(f"## Conversation Summary\n{self.summary}")
        
        # Add key facts
        if self.key_facts:
            parts.append("\n## Key Facts Mentioned")
            for key, value in self.key_facts.items():
                parts.append(f"- {key}: {value}")
        
        # Add recent turns
        if self.raw_history:
            parts.append("\n## Recent Conversation")
            for turn in self.raw_history[-3:]:  # Last 3 turns
                role = turn['role'].upper()
                msg = turn['message'][:100] + "..." if len(turn['message']) > 100 else turn['message']
                parts.append(f"{role}: {msg}")
        
        return "\n".join(parts) if parts else "No prior context."
    
    def is_verified(self) -> bool:
        """Check if user identity has been verified."""
        return self.key_facts.get("identity_verified", False)
    
    def mark_verified(self, method: str):
        """Mark user as verified."""
        self.key_facts["identity_verified"] = True
        self.key_facts["verification_method"] = method
        self.key_facts["verification_time"] = time.time()


# Global memory store per session
_session_memories: Dict[str, ConversationMemory] = {}


def get_memory(session_id: str) -> ConversationMemory:
    """Get or create memory for a session.
    
    Args:
        session_id: The conversation session ID
        
    Returns:
        ConversationMemory for the session
    """
    if session_id not in _session_memories:
        _session_memories[session_id] = ConversationMemory()
    return _session_memories[session_id]


def clear_memory(session_id: str):
    """Clear memory for a session.
    
    Args:
        session_id: Session to clear
    """
    if session_id in _session_memories:
        del _session_memories[session_id]


def get_conversation_context(session_id: str) -> str:
    """Retrieve the conversation context and key facts for a session.

    Use this to recall what the customer has already told you (account
    references, prior questions, verification status) so you stay consistent
    across turns.

    Args:
        session_id: The conversation session ID.

    Returns:
        A formatted summary of prior context, or a note that none exists.
    """
    memory = get_memory(session_id)
    return memory.get_context()


def clear_conversation_memory(session_id: str) -> str:
    """Clear stored conversation memory for a session.

    Args:
        session_id: The conversation session ID to clear.

    Returns:
        Confirmation message.
    """
    clear_memory(session_id)
    return f"Conversation memory cleared for session {session_id}."


def get_memory_stats() -> Dict:
    """Get statistics about memory usage.
    
    Returns:
        Dict with memory stats
    """
    return {
        "active_sessions": len(_session_memories),
        "total_facts_stored": sum(
            len(m.key_facts) for m in _session_memories.values()
        ),
        "total_turns_stored": sum(
            len(m.raw_history) for m in _session_memories.values()
        ),
    }
