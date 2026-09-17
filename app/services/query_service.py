"""Phase 7 — Client Query Escalation Service"""
import json
import logging
from typing import Optional

from app.extensions import db
from app.models.client import Client
from app.models.query import ClientQuery
from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are a compliance-aware AI assistant for a financial advisory practice.

A client has submitted a question. Your task:
1. Provide a brief, helpful AI response if the question is factual/general knowledge.
2. Determine whether the question MUST be escalated to the human practitioner.
3. Always escalate questions involving: specific financial advice, investment recommendations, personal portfolio decisions, regulatory matters, complaints, or anything requiring professional judgement.

Respond with JSON:
{
  "ai_response": "A neutral, helpful reply. For escalated questions, say 'Your adviser will get back to you shortly.'",
  "escalated": true | false,
  "escalation_reason": "Why this needs practitioner review, or null if not escalated"
}
Rules: Respond ONLY with the JSON object. No markdown fences.
""".strip()


def process_query(client: Client, question: str, practitioner_id: str) -> ClientQuery:
    """Call Gemini to draft an AI response + decide escalation, persist and return."""
    try:
        raw = call_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_content=f"Client: {client.name}\nQuestion: {question}",
            max_tokens=512,
        )
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
    except Exception as exc:
        logger.exception("Query processing failed")
        data = {
            "ai_response": "Your adviser will get back to you shortly.",
            "escalated": True,
            "escalation_reason": f"AI processing error: {exc}",
        }

    query = ClientQuery(
        client_id=client.id,
        practitioner_id=practitioner_id,
        question=question,
        ai_response=data.get("ai_response", ""),
        escalated=data.get("escalated", True),
        escalation_reason=data.get("escalation_reason"),
    )
    db.session.add(query)
    db.session.commit()
    return query
