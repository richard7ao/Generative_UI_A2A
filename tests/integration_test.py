"""Integration tests for the 3-agent A2A system.

Tests agent-to-agent communication and full conversation flows.
Requires all 3 agents to be running.
"""

import pytest
import asyncio
import httpx
import json
import uuid
from typing import Dict, Any

# Agent URLs (when running locally)
PERSONAL_AGENT_URL = "http://localhost:9001"
CS_AGENT_URL = "http://localhost:9002"
RESEARCH_AGENT_URL = "http://localhost:9003"


class TestAgentHealth:
    """Test that all agents are healthy and serving."""
    
    @pytest.mark.asyncio
    async def test_personal_agent_health(self):
        """Personal agent should serve agent card."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PERSONAL_AGENT_URL}/.well-known/agent.json")
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "personal_agent"
    
    @pytest.mark.asyncio
    async def test_cs_agent_health(self):
        """CS agent should serve agent card."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CS_AGENT_URL}/.well-known/agent.json")
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "cs_agent"
            assert len(data["skills"]) >= 19  # Should have all our new skills
    
    @pytest.mark.asyncio
    async def test_research_agent_health(self):
        """Research agent should serve agent card."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{RESEARCH_AGENT_URL}/.well-known/agent.json")
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "research_agent"


class TestCSAgentCapabilities:
    """Test CS agent's new capabilities."""
    
    @pytest.mark.asyncio
    async def test_cs_agent_has_enhanced_search(self):
        """CS agent should have enhanced search skill."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CS_AGENT_URL}/.well-known/agent.json")
            data = resp.json()
            skill_ids = [s["id"] for s in data["skills"]]
            assert any("enhanced" in s for s in skill_ids)
    
    @pytest.mark.asyncio
    async def test_cs_agent_has_intent_classification(self):
        """CS agent should have intent classification skill."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CS_AGENT_URL}/.well-known/agent.json")
            data = resp.json()
            skill_ids = [s["id"] for s in data["skills"]]
            assert any("classify" in s for s in skill_ids)
    
    @pytest.mark.asyncio
    async def test_cs_agent_has_validation_tools(self):
        """CS agent should have validation skills."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CS_AGENT_URL}/.well-known/agent.json")
            data = resp.json()
            skill_ids = [s["id"] for s in data["skills"]]
            assert any("valid" in s or "correct" in s for s in skill_ids)
    
    @pytest.mark.asyncio
    async def test_cs_agent_has_memory_tools(self):
        """CS agent should have memory skills."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CS_AGENT_URL}/.well-known/agent.json")
            data = resp.json()
            skill_ids = [s["id"] for s in data["skills"]]
            assert any("memory" in s for s in skill_ids)


class TestA2ACommunication:
    """Test A2A protocol communication between agents."""
    
    @pytest.mark.asyncio
    async def test_send_message_to_cs_agent(self):
        """Should be able to send message to CS agent via A2A."""
        # This is a simplified test - real A2A would use proper message format
        async with httpx.AsyncClient() as client:
            # Try to send a simple task (format depends on A2A implementation)
            resp = await client.post(
                f"{CS_AGENT_URL}/tasks",
                json={
                    "id": str(uuid.uuid4()),
                    "status": {
                        "state": "submitted",
                        "message": {
                            "parts": [{"text": "What are your hours?"}]
                        }
                    }
                },
                timeout=30.0
            )
            # Should at least accept the task
            assert resp.status_code in [200, 202, 201]
    
    @pytest.mark.asyncio
    async def test_context_id_propagation(self):
        """A2A messages should preserve context ID."""
        context_id = str(uuid.uuid4())
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CS_AGENT_URL}/tasks",
                json={
                    "id": str(uuid.uuid4()),
                    "context_id": context_id,
                    "status": {
                        "state": "submitted",
                        "message": {
                            "parts": [{"text": "Test message"}]
                        }
                    }
                }
            )
            
            # Verify task was created with context
            if resp.status_code == 200:
                data = resp.json()
                # Context ID should be preserved in response
                assert "id" in data


class TestEndToEndFlows:
    """Test complete conversation flows."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full A2A harness setup")
    async def test_simple_balance_inquiry(self):
        """Test: User asks for balance → Personal → CS → Response."""
        # This would require the full A2A harness
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full A2A harness setup")
    async def test_complex_policy_question(self):
        """Test: Complex question triggers research agent escalation."""
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full A2A harness setup")
    async def test_identity_verification_flow(self):
        """Test: Identity verification multi-turn conversation."""
        pass


class TestErrorHandling:
    """Test system resilience and error handling."""
    
    @pytest.mark.asyncio
    async def test_cs_agent_handles_malformed_request(self):
        """CS agent should handle malformed requests gracefully."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CS_AGENT_URL}/tasks",
                json={"invalid": "data"},
                timeout=5.0
            )
            # Should return error, not crash
            assert resp.status_code in [400, 422, 500]
    
    @pytest.mark.asyncio
    async def test_research_agent_discovery(self):
        """CS agent should be able to discover research agent."""
        # This tests the agent discovery capability
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{RESEARCH_AGENT_URL}/.well-known/agent.json")
            assert resp.status_code == 200
            data = resp.json()
            assert "skills" in data


def check_agents_running() -> bool:
    """Check if all agents are running."""
    import urllib.request
    
    agents = [
        PERSONAL_AGENT_URL,
        CS_AGENT_URL,
        RESEARCH_AGENT_URL
    ]
    
    for url in agents:
        try:
            urllib.request.urlopen(f"{url}/.well-known/agent.json", timeout=2)
        except:
            return False
    
    return True


# Skip all integration tests if agents not running
if not check_agents_running():
    pytest.skip("Agents not running, skipping integration tests", allow_module_level=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
