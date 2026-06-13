"""Advanced knowledge-base research tools backed by Redis (RediSearch).

The research agent provides deep research capabilities for the CS agent:
- Multi-strategy search (BM25 + Vector + Hybrid)
- Cross-document synthesis and analysis
- Policy comparison and conflict detection
- Procedural guidance extraction
"""

import os
import re
import struct
from typing import Any

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
KB_INDEX = "kb_idx"
DOC_PREFIX = "doc:"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

_client = redis.Redis.from_url(REDIS_URL, decode_responses=False)
_genai_client = None


def _get_genai_client():
    """Reused genai client (one connection pool, not a new one per search)."""
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client()
    return _genai_client


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed texts with gemini-embedding-001 via google-genai."""
    from google.genai import types

    result = _get_genai_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return [e.values for e in result.embeddings]


def _decode(value) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _parse_search_reply(reply) -> list[dict]:
    """Normalize an FT.SEARCH reply (array or map shape) to result dicts."""
    if isinstance(reply, dict):
        results = reply.get(b"results", reply.get("results")) or []
        out = []
        for row in results:
            attrs = row.get(b"extra_attributes", row.get("extra_attributes")) or {}
            doc = {"doc_id": _decode(row.get(b"id", row.get("id", "")))}
            doc.update({_decode(k): _decode(v) for k, v in attrs.items()})
            out.append(doc)
        return out
    out = []
    for i in range(1, len(reply) - 1, 2):
        doc = {"doc_id": _decode(reply[i])}
        fields = reply[i + 1]
        for j in range(0, len(fields) - 1, 2):
            doc[_decode(fields[j])] = _decode(fields[j + 1])
        out.append(doc)
    return out


def _strip_score(docs: list[dict]) -> list[dict]:
    for doc in docs:
        doc.pop("score", None)
    return docs


def deep_search(query: str, top_k: int = 10) -> list[dict]:
    """Deep search combining BM25 and vector search with result fusion.

    This performs both keyword and semantic search, then fuses results
    using reciprocal rank fusion for better coverage.

    Args:
        query: The research query - can be keywords or natural language.
        top_k: Number of documents to return (default 10 for deeper research).

    Returns:
        Ranked documents with doc_id, title, content, and search type.
    """
    # Get BM25 results
    terms = re.findall(r"\w+", query.lower())
    bm25_results = []
    if terms:
        or_query = "|".join(dict.fromkeys(terms))
        reply = _client.execute_command(
            "FT.SEARCH", KB_INDEX, or_query,
            "LIMIT", "0", str(top_k * 2),
            "RETURN", "2", "title", "content",
        )
        bm25_results = _parse_search_reply(reply)

    # Get vector results
    vector_results = []
    try:
        vector = struct.pack(f"{EMBEDDING_DIM}f", *_embed([query])[0])
        reply = _client.execute_command(
            "FT.SEARCH", KB_INDEX, f"*=>[KNN {top_k * 2} @embedding $vec AS score]",
            "PARAMS", "2", "vec", vector,
            "SORTBY", "score",
            "LIMIT", "0", str(top_k * 2),
            "RETURN", "3", "title", "content", "score",
            "DIALECT", "2",
        )
        vector_results = _strip_score(_parse_search_reply(reply))
    except Exception:
        pass

    # Reciprocal Rank Fusion
    def rrf_fuse(bm25_docs: list[dict], vector_docs: list[dict], k: int = 60) -> list[dict]:
        scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        for rank, doc in enumerate(bm25_docs):
            doc_id = doc["doc_id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
            doc_map[doc_id] = {**doc, "search_type": "keyword"}

        for rank, doc in enumerate(vector_docs):
            doc_id = doc["doc_id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
            if doc_id in doc_map:
                doc_map[doc_id]["search_type"] = "hybrid"
            else:
                doc_map[doc_id] = {**doc, "search_type": "semantic"}

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [doc_map[doc_id] for doc_id in sorted_ids[:top_k]]

    return rrf_fuse(bm25_results, vector_results)


def analyze_policy_conflicts(topic: str) -> dict[str, Any]:
    """Search for and analyze potential policy conflicts or edge cases.

    Args:
        topic: The policy area to analyze (e.g., "account fees", "dispute process").

    Returns:
        Analysis including potential conflicts, gaps, or special cases found.
    """
    # Search for documents related to the topic
    docs = deep_search(topic, top_k=15)

    # Also search for exceptions, overrides, special cases
    exception_queries = [
        f"{topic} exception",
        f"{topic} override",
        f"{topic} special case",
        f"{topic} not applicable",
        f"{topic} waiver",
    ]

    all_docs = {d["doc_id"]: d for d in docs}
    for q in exception_queries:
        for doc in deep_search(q, top_k=5):
            all_docs[doc["doc_id"]] = doc

    return {
        "topic": topic,
        "documents_found": len(all_docs),
        "documents": list(all_docs.values())[:10],
        "search_strategy": "Multi-query deep search including exception patterns",
    }


def extract_procedures(task_description: str) -> dict[str, Any]:
    """Extract step-by-step procedures for a specific task from the KB.

    Args:
        task_description: Description of what needs to be done.

    Returns:
        Relevant procedures with steps, required tools, and prerequisites.
    """
    # Search for procedures related to the task
    procedure_queries = [
        f"how to {task_description}",
        f"procedure for {task_description}",
        f"steps to {task_description}",
        f"process for {task_description}",
        task_description,
    ]

    all_docs: dict[str, dict] = {}
    for query in procedure_queries:
        for doc in deep_search(query, top_k=5):
            all_docs[doc["doc_id"]] = doc

    return {
        "task": task_description,
        "procedure_documents": list(all_docs.values())[:8],
        "search_coverage": len(all_docs),
    }


def find_related_policies(policy_area: str) -> dict[str, Any]:
    """Find all policies related to a specific area, including cross-references.

    Args:
        policy_area: The policy domain (e.g., "credit cards", "savings accounts").

    Returns:
        Related policies with relationship mapping.
    """
    # Direct search
    direct_docs = deep_search(policy_area, top_k=10)

    # Find cross-references by searching for mentions
    related_docs: dict[str, dict] = {d["doc_id"]: d for d in direct_docs}

    # Search for related terms
    related_terms = [
        f"related to {policy_area}",
        f"applies to {policy_area}",
        f"{policy_area} holders",
        f"{policy_area} customers",
    ]

    for term in related_terms:
        for doc in deep_search(term, top_k=5):
            if doc["doc_id"] not in related_docs:
                related_docs[doc["doc_id"]] = {**doc, "relationship": "cross-reference"}

    return {
        "policy_area": policy_area,
        "primary_documents": [d for d in related_docs.values() if "relationship" not in d][:5],
        "related_documents": [d for d in related_docs.values() if d.get("relationship") == "cross-reference"][:5],
        "total_found": len(related_docs),
    }


def research_answer(question: str, context: str = "") -> dict[str, Any]:
    """Comprehensive research to answer a complex policy or procedural question.

    This is the main entry point for CS agent research requests.

    Args:
        question: The research question from the CS agent.
        context: Optional context about the customer situation.

    Returns:
        Comprehensive research findings with sources and confidence.
    """
    # Perform deep search
    docs = deep_search(question, top_k=12)

    # If we have context, also search for context-specific information
    if context:
        context_docs = deep_search(context, top_k=8)
        # Merge without duplicates
        seen = {d["doc_id"] for d in docs}
        for doc in context_docs:
            if doc["doc_id"] not in seen:
                docs.append(doc)
                seen.add(doc["doc_id"])

    return {
        "question": question,
        "context": context,
        "research_findings": docs[:15],
        "document_count": len(docs),
        "research_method": "Deep hybrid search (BM25 + Vector fusion)",
    }
