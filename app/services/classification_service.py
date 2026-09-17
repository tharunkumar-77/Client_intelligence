import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.llm_client import call_llm
from app.vertical.loader import VerticalConfig

logger = logging.getLogger(__name__)


@dataclass
class ProposedField:
    key: str
    label: str
    type: str = "text"


@dataclass
class ClassificationResult:
    segment: str
    risk_level: str
    urgency: str
    recommended_approach: str
    confidence: float
    reasoning: str
    proposed_new_fields: List[ProposedField] = field(default_factory=list)
    raw_response: str = ""
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment": self.segment,
            "risk_level": self.risk_level,
            "urgency": self.urgency,
            "recommended_approach": self.recommended_approach,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "proposed_new_fields": [
                {"key": f.key, "label": f.label, "type": f.type}
                for f in self.proposed_new_fields
            ],
            "success": self.success,
            "error": self.error,
        }


def classify_intake(
    raw_response: Dict[str, Any],
    vertical_config: VerticalConfig,
) -> ClassificationResult:
    """
    Classify an intake submission using the vertical-specific prompt template.
    Returns a structured ClassificationResult including any proposed new schema fields.
    """
    system_prompt = _build_system_prompt(vertical_config)
    user_content = _build_user_content(raw_response, vertical_config)

    try:
        raw_text = call_llm(system_prompt=system_prompt, user_content=user_content)
        return _parse_response(raw_text)
    except Exception as exc:
        logger.exception("Classification LLM call failed")
        return ClassificationResult(
            segment="Unknown",
            risk_level="Unknown",
            urgency="Unknown",
            recommended_approach="Classification failed — please review manually.",
            confidence=0.0,
            reasoning="",
            success=False,
            error=str(exc),
        )


def _build_system_prompt(vc: VerticalConfig) -> str:
    return vc.classification_prompt_template.strip()


def _build_user_content(raw: Dict[str, Any], vc: VerticalConfig) -> str:
    label_map = {q["key"]: q.get("label", q["key"]) for q in vc.intake_questions}
    lines = ["Client intake response:\n"]
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        lines.append(f"  {label_map.get(key, key)}: {value}")
    return "\n".join(lines)


def _parse_response(raw_text: str) -> ClassificationResult:
    text = raw_text.strip()
    # Strip markdown fences if model adds them despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON: {exc}\nRaw (first 500 chars): {raw_text[:500]}"
        )

    proposed_fields = [
        ProposedField(key=pf["key"], label=pf.get("label", pf["key"]), type=pf.get("type", "text"))
        for pf in data.get("proposed_new_fields", [])
        if isinstance(pf, dict) and "key" in pf
    ]

    return ClassificationResult(
        segment=data.get("segment", "Other"),
        risk_level=data.get("risk_level", "Unknown"),
        urgency=data.get("urgency", "Unknown"),
        recommended_approach=data.get("recommended_approach", ""),
        confidence=float(data.get("confidence", 0.0)),
        reasoning=data.get("reasoning", ""),
        proposed_new_fields=proposed_fields,
        raw_response=raw_text,
        success=True,
    )
