"""Tests for the classification service."""
import json
from unittest.mock import patch

import pytest

from app.services.classification_service import (
    ClassificationResult,
    _parse_response,
    classify_intake,
)
from app.vertical.loader import load_vertical_config


VALID_JSON_RESPONSE = json.dumps({
    "segment": "Business Owner",
    "risk_level": "High",
    "urgency": "High",
    "recommended_approach": "Immediate cash-flow analysis recommended.",
    "confidence": 0.91,
    "reasoning": "Complex business finances with stated urgency.",
    "proposed_new_fields": [
        {"key": "business_turnover", "label": "Business Annual Turnover", "type": "text"}
    ],
})


def test_parse_valid_json():
    result = _parse_response(VALID_JSON_RESPONSE)
    assert result.segment == "Business Owner"
    assert result.risk_level == "High"
    assert result.confidence == 0.91
    assert len(result.proposed_new_fields) == 1
    assert result.proposed_new_fields[0].key == "business_turnover"


def test_parse_strips_markdown_fences():
    fenced = f"```json\n{VALID_JSON_RESPONSE}\n```"
    result = _parse_response(fenced)
    assert result.segment == "Business Owner"


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="invalid JSON"):
        _parse_response("not json at all")


def test_classify_intake_calls_llm(app):
    vc = load_vertical_config("financial_advisory")
    intake_data = {
        "full_name": "Test User",
        "occupation": "Doctor",
        "annual_income_range": "Above ₹1Cr",
        "risk_tolerance": "Low",
    }
    with app.app_context():
        with patch("app.services.classification_service.call_llm") as mock_llm:
            mock_llm.return_value = VALID_JSON_RESPONSE
            result = classify_intake(intake_data, vc)

        assert result.success is True
        assert result.segment == "Business Owner"
        mock_llm.assert_called_once()


def test_classify_intake_handles_llm_error(app):
    vc = load_vertical_config("financial_advisory")
    with app.app_context():
        with patch("app.services.classification_service.call_llm", side_effect=Exception("API down")):
            result = classify_intake({}, vc)

        assert result.success is False
        assert "API down" in result.error
        assert result.segment == "Unknown"
