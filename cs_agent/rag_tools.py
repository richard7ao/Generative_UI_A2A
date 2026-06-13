"""Knowledge-base search tools backed by Redis (RediSearch).

kb_search_bm25: full-text BM25 search (OR-semantics keyword query).
kb_search_vector: HNSW vector search over gemini-embedding-001 embeddings
(available only when the index was built with embeddings).

Replies are parsed via execute_command so both the classic array reply and
the Redis 8 map-style reply work regardless of redis-py version."""

import os
import re
import struct
from typing import List

import redis

# Query expansion synonyms for better recall
QUERY_EXPANSIONS = {
    # Account types
    "account": ["account", "checking", "savings", "debit"],
    "overdraft": ["overdraft", "negative balance", "insufficient funds", "NSF", "fee"],
    # Transaction terms
    "transaction": ["transaction", "payment", "transfer", "charge", "debit", "credit"],
    "dispute": ["dispute", "fraud", "unauthorized", "chargeback", "claim"],
    # Card terms
    "card": ["card", "credit card", "debit card", "plastic"],
    "limit": ["limit", "cap", "maximum", "threshold", "ceiling"],
    # Service terms
    "referral": ["referral", "refer a friend", "invite", "recommendation"],
    "application": ["application", "apply", "request", "submission"],
    # Policy terms
    "fee": ["fee", "charge", "cost", "price", "rate"],
    "policy": ["policy", "rule", "guideline", "procedure", "regulation"],
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
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

    # Reduced-dim output is unnormalized; the index uses COSINE, so that's fine.
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


def expand_query(query: str) -> List[str]:
    """Expand query with synonyms for better recall.
    
    Args:
        query: Original search query
        
    Returns:
        List of expanded queries including synonyms
    """
    query_lower = query.lower()
    expanded_queries = [query]  # Always include original
    
    for keyword, synonyms in QUERY_EXPANSIONS.items():
        if keyword in query_lower:
            # Create variations with each synonym
            for synonym in synonyms:
                if synonym != keyword:
                    expanded = query_lower.replace(keyword, synonym)
                    if expanded not in expanded_queries:
                        expanded_queries.append(expanded)
    
    return expanded_queries


def deduplicate_results(results_list: List[list[dict]]) -> list[dict]:
    """Deduplicate and merge search results from multiple queries.
    
    Args:
        results_list: List of result lists from different queries
        
    Returns:
        Deduplicated merged results
    """
    seen_ids = set()
    merged = []
    
    for results in results_list:
        for doc in results:
            doc_id = doc.get("doc_id")
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                merged.append(doc)
    
    return merged


def kb_search_bm25(query: str, top_k: int = 5) -> list[dict]:
    """Full-text (BM25) search over the Rho-Bank knowledge base.

    Args:
        query: Keywords or a short phrase to search for. Matching is ranked,
            so extra keywords help rather than hurt.
        top_k: Number of documents to return.

    Returns:
        Matching documents with doc_id, title, and full content.
    """
    terms = re.findall(r"\w+", query.lower())
    if not terms:
        return []
    # OR-join: RediSearch defaults to AND, which zeroes out long queries.
    or_query = "|".join(dict.fromkeys(terms))
    reply = _client.execute_command(
        "FT.SEARCH", KB_INDEX, or_query,
        "LIMIT", "0", str(top_k),
        "RETURN", "2", "title", "content",
    )
    return _parse_search_reply(reply)


def kb_search_vector(query: str, top_k: int = 5) -> list[dict]:
    """Semantic (vector) search over the Rho-Bank knowledge base.

    Better than kb_search_bm25 when the query is a natural-language question
    rather than exact keywords.

    Args:
        query: A natural-language question or description.
        top_k: Number of documents to return.

    Returns:
        Matching documents with doc_id, title, and full content; or an error
        entry telling you to fall back to kb_search_bm25.
    """
    try:
        vector = struct.pack(f"{EMBEDDING_DIM}f", *_embed([query])[0])
        reply = _client.execute_command(
            "FT.SEARCH", KB_INDEX, f"*=>[KNN {top_k} @embedding $vec AS score]",
            "PARAMS", "2", "vec", vector,
            "SORTBY", "score",
            "LIMIT", "0", str(top_k),
            "RETURN", "3", "title", "content", "score",
            "DIALECT", "2",
        )
        return _strip_score(_parse_search_reply(reply))
    except Exception as e:
        return [
            {
                "error": f"Vector search unavailable ({type(e).__name__}). "
                "Use kb_search_bm25 with keywords instead."
            }
        ]


def kb_search_enhanced(query: str, top_k: int = 5) -> list[dict]:
    """Enhanced search with query expansion for better recall.
    
    Performs multiple searches with expanded query variations and merges
    results, providing better coverage than single-query search.
    
    Args:
        query: Original search query
        top_k: Number of documents to return (per query variation)
        
    Returns:
        Merged, deduplicated search results
    """
    # Expand query with synonyms
    expanded_queries = expand_query(query)
    
    # Search with each variation
    all_results = []
    for expanded_query in expanded_queries:
        results = kb_search_bm25(expanded_query, top_k=min(top_k, 3))
        all_results.append(results)
    
    # Deduplicate and return merged results
    merged = deduplicate_results(all_results)
    
    # Return top_k of merged results
    return merged[:top_k]
