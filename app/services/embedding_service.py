"""
Phase 10 — Semantic Intelligence: Gemini text-embedding-004 + pgvector
Provides:
  embed_text(text)          → 768-dim float list
  embed_client(client)      → same, from client profile
  semantic_search(query, practitioner_id) → ranked client list
"""
import json
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

_EMBED_MODEL = "models/text-embedding-004"
_DIM = 768


def embed_text(text: str, task: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
    """Call Gemini text-embedding-004 and return a 768-dim vector, or None on error."""
    if not text or not text.strip():
        return None
    try:
        import google.generativeai as genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model=_EMBED_MODEL,
            content=text.strip(),
            task_type=task,
        )
        return result["embedding"]
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None


def build_client_text(client) -> str:
    """Serialise a client record into a rich text blob for embedding."""
    parts = [
        f"Client: {client.name}",
        f"Segment: {client.segment.name if client.segment else 'Unknown'}",
        f"Risk: {client.risk_level or 'Unknown'}",
        f"Urgency: {client.urgency or 'Unknown'}",
    ]
    if client.attributes:
        for k, v in (client.attributes or {}).items():
            parts.append(f"{k.replace('_', ' ').title()}: {v}")
    # Include recent note summaries if available
    try:
        from app.models.note import Note
        recent = (
            Note.query.filter_by(client_id=client.id)
            .order_by(Note.created_at.desc())
            .limit(3)
            .all()
        )
        for n in recent:
            so = n.structured_output or {}
            if so.get("summary"):
                parts.append(f"Session: {so['summary']}")
            if so.get("sentiment"):
                parts.append(f"Sentiment: {so['sentiment']}")
    except Exception:
        pass
    return ". ".join(parts)


def embed_client(client) -> Optional[List[float]]:
    """Generate a fresh embedding for a client record."""
    return embed_text(build_client_text(client), task="RETRIEVAL_DOCUMENT")


def semantic_search(query: str, practitioner_id: str, limit: int = 10) -> List[dict]:
    """
    Embed the query and find the closest client vectors using pgvector cosine distance.
    Falls back to empty list if embeddings unavailable.
    """
    from app.models.client import Client
    from app.extensions import db
    from sqlalchemy import text as sql_text

    query_vec = embed_text(query, task="RETRIEVAL_QUERY")
    if query_vec is None:
        return []

    # pgvector cosine distance: <=> operator (lower = more similar)
    try:
        rows = db.session.execute(
            sql_text("""
                SELECT id, name, email, risk_level, urgency,
                       (embedding <=> CAST(:vec AS vector)) AS distance
                FROM clients
                WHERE practitioner_id = :pid
                  AND embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT :lim
            """),
            {
                "vec": json.dumps(query_vec),
                "pid": practitioner_id,
                "lim":  limit,
            },
        ).fetchall()
    except Exception as exc:
        logger.warning("pgvector search failed: %s", exc)
        return []

    results = []
    for row in rows:
        c = Client.query.get(row.id)
        if c:
            d = c.to_dict()
            d["similarity_score"] = round(1 - float(row.distance), 4)
            results.append(d)
    return results


def backfill_embeddings(practitioner_id: str) -> int:
    """
    Generate embeddings for all clients that don't have one yet.
    Returns the count of updated rows.
    """
    from app.models.client import Client
    from app.extensions import db

    clients = Client.query.filter_by(practitioner_id=practitioner_id).all()
    updated = 0
    for c in clients:
        if c.embedding is None:
            vec = embed_client(c)
            if vec:
                c.embedding = vec
                updated += 1
    if updated:
        db.session.commit()
    logger.info("Backfilled embeddings for %d clients", updated)
    return updated
