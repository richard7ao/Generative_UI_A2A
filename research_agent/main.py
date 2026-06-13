"""Serve the research agent over A2A. Run: uvicorn main:app --host 0.0.0.0 --port 9003

Ingest runs first (readiness gate): the agent card is only served once the
knowledge-base index is built."""

import auth_hardening  # noqa: F401  resilient OAuth token-refresh transport (import first)

import os

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from ingest import build_index

build_index()

from agent import root_agent  # noqa: E402  (import after the readiness gate)

app = to_a2a(root_agent, host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "9003")))
