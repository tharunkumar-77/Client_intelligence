"""Phase 5 — Triage & Lead Ranking Service"""
import json
import logging
from typing import List

from app.models.client import Lead
from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are an expert financial advisory business development analyst.

Given a list of leads with their attributes, rank them by urgency and estimated value.
Return a JSON array (same length as input) where each element has:
{
  "id": "<lead_id>",
  "priority_score": <0-100 integer>,
  "priority_label": "High" | "Medium" | "Low",
  "reasoning": "One sentence explaining the ranking"
}
Rules:
- Respond ONLY with the JSON array. No markdown fences.
- Higher score = higher priority. Consider: income signals, urgency keywords, time-sensitive goals.
""".strip()


def rank_leads(leads: List[Lead]) -> List[dict]:
    """Use Gemini to rank a list of leads by priority. Returns enriched dicts."""
    if not leads:
        return []

    lead_summaries = []
    for ld in leads:
        lead_summaries.append({
            "id": ld.id,
            "name": ld.name,
            "attributes": ld.attributes or {},
        })

    try:
        raw = call_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_content=json.dumps(lead_summaries, indent=2),
            max_tokens=1024,
        )
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        rankings = json.loads(text)
    except Exception as exc:
        logger.exception("Lead ranking failed: %s", exc)
        rankings = [{"id": ld.id, "priority_score": 50, "priority_label": "Medium",
                     "reasoning": "AI ranking unavailable."} for ld in leads]

    # Merge lead dict with ranking
    rank_map = {r["id"]: r for r in rankings}
    results = []
    for ld in leads:
        base = ld.to_dict()
        base.update(rank_map.get(ld.id, {"priority_score": 50, "priority_label": "Medium", "reasoning": ""}))
        results.append(base)

    results.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return results
