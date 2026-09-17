import os
import yaml
from dataclasses import dataclass, field
from functools import lru_cache

VERTICAL_CONFIGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "vertical_configs",
)


@dataclass
class EscalationConfig:
    ai_client_response_allowed: bool = False
    confidence_threshold_for_autocommit: float = 0.75


@dataclass
class VerticalConfig:
    vertical: str
    display: dict
    intake_questions: list
    classification_prompt_template: str
    escalation: EscalationConfig
    compliance_notes: str = ""

    @property
    def client_label(self) -> str:
        return self.display.get("client_label", "Client")

    @property
    def session_label(self) -> str:
        return self.display.get("session_label", "Session")


@lru_cache(maxsize=None)
def load_vertical_config(vertical: str) -> VerticalConfig:
    config_path = os.path.join(VERTICAL_CONFIGS_DIR, f"{vertical}.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"No vertical config found for '{vertical}' at {config_path}"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    esc = raw.get("escalation", {})
    return VerticalConfig(
        vertical=raw["vertical"],
        display=raw.get("display", {}),
        intake_questions=raw.get("intake_questions", []),
        classification_prompt_template=raw.get("classification_prompt_template", ""),
        escalation=EscalationConfig(
            ai_client_response_allowed=esc.get("ai_client_response_allowed", False),
            confidence_threshold_for_autocommit=esc.get(
                "confidence_threshold_for_autocommit", 0.75
            ),
        ),
        compliance_notes=raw.get("compliance_notes", ""),
    )


def reload_vertical_configs() -> None:
    """Clear LRU cache to force config reload (call on SIGHUP or config edit)."""
    load_vertical_config.cache_clear()
