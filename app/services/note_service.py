"""
Phase 2 — Note Intelligence Service
Extracts structured data from free-form practitioner notes using Gemini.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.extensions import db
from app.models.client import Client
from app.models.note import Note, Reminder
from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are an expert financial advisory assistant helping a practitioner structure their session notes.

Given a raw practitioner note about a client session, extract and return a JSON object with exactly these keys:
- summary: string — one-sentence summary of the session
- sentiment: one of ["Positive", "Neutral", "Anxious", "Concerned", "Negative"]
- action_items: list of strings — concrete follow-up actions the practitioner must take
- key_facts: object — any new or updated facts about the client (e.g. {"portfolio_value": "1.2M", "life_event": "retirement next year"})
- follow_up_date: ISO date string (YYYY-MM-DD) if a specific follow-up is mentioned, else null
- follow_up_note: string — what the follow-up should be about, or null

Rules:
- Respond ONLY with the JSON object. No markdown fences, no text outside the JSON.
- action_items should be short imperative phrases (e.g. "Send rebalancing proposal", "Book review meeting").
- key_facts keys must be snake_case.
- If nothing specific is mentioned for a field, use an empty list / empty object / null.
""".strip()


@dataclass
class NoteResult:
    note_id: str
    summary: str
    sentiment: str
    action_items: List[str] = field(default_factory=list)
    key_facts: Dict[str, Any] = field(default_factory=dict)
    follow_up_date: Optional[str] = None
    follow_up_note: Optional[str] = None
    raw_response: str = ""
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "note_id": self.note_id,
            "summary": self.summary,
            "sentiment": self.sentiment,
            "action_items": self.action_items,
            "key_facts": self.key_facts,
            "follow_up_date": self.follow_up_date,
            "follow_up_note": self.follow_up_note,
            "success": self.success,
            "error": self.error,
        }


def process_note(
    client: Client,
    raw_text: str,
    practitioner_id: str,
) -> NoteResult:
    """
    Persist raw note, call Gemini for extraction, persist structured output.
    Returns a NoteResult with all extracted fields.
    """
    # 1 — Persist raw note immediately
    note = Note(
        client_id=client.id,
        practitioner_id=practitioner_id,
        raw_input=raw_text,
        input_type="text",
    )
    db.session.add(note)
    db.session.flush()  # get note.id before LLM call

    # 2 — Build context-aware user content
    client_context = (
        f"Client name: {client.name}\n"
        f"Segment: {client.segment.name if client.segment else 'Unknown'}\n"
        f"Risk level: {client.risk_level or 'Unknown'}\n"
        f"Known attributes: {json.dumps(client.attributes or {}, indent=2)}\n\n"
        f"Session note:\n{raw_text}"
    )

    try:
        raw_llm = call_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_content=client_context,
            max_tokens=1024,
        )
        extracted = _parse(raw_llm)
    except Exception as exc:
        logger.exception("Note extraction LLM call failed note_id=%s", note.id)
        note.structured_output = {"error": str(exc)}
        db.session.commit()
        return NoteResult(note_id=note.id, summary="", sentiment="Neutral",
                          success=False, error=str(exc))

    # 3 — Persist structured output
    note.structured_output = extracted
    db.session.flush()

    # 4 — Merge key_facts back into client.attributes
    if extracted.get("key_facts"):
        attrs = dict(client.attributes or {})
        attrs.update(extracted["key_facts"])
        client.attributes = attrs

    # 5 — Auto-create reminder if follow_up_date present
    if extracted.get("follow_up_date"):
        try:
            due = datetime.fromisoformat(extracted["follow_up_date"]).replace(tzinfo=timezone.utc)
            reminder = Reminder(
                note_id=note.id,
                client_id=client.id,
                practitioner_id=practitioner_id,
                due_at=due,
                message=extracted.get("follow_up_note") or f"Follow-up with {client.name}",
            )
            db.session.add(reminder)
        except ValueError:
            logger.warning("Unparseable follow_up_date: %s", extracted["follow_up_date"])

    db.session.commit()

    # ── Background-style: regenerate client embedding with new note context ──
    try:
        from app.services.embedding_service import embed_client, embed_text
        # Embed the note itself
        note_vec = embed_text(raw_text)
        if note_vec:
            note.embedding = note_vec
        # Re-embed client profile (now includes this note's summary)
        client_vec = embed_client(client)
        if client_vec:
            client.embedding = client_vec
        db.session.commit()
    except Exception as emb_exc:
        logger.warning("Embedding step failed (non-fatal): %s", emb_exc)

    return NoteResult(
        note_id=note.id,
        summary=extracted.get("summary", ""),
        sentiment=extracted.get("sentiment", "Neutral"),
        action_items=extracted.get("action_items", []),
        key_facts=extracted.get("key_facts", {}),
        follow_up_date=extracted.get("follow_up_date"),
        follow_up_note=extracted.get("follow_up_note"),
        raw_response=raw_llm,
        success=True,
    )


def _parse(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned invalid JSON: {exc}\nRaw: {raw_text[:500]}")
