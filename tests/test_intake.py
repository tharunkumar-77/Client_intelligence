"""Tests for the intake webhook pipeline."""
import json
from unittest.mock import MagicMock, patch

from app.models.practitioner import Practitioner
from app.models.segment import Segment
from app.extensions import db


SAMPLE_INTAKE = {
    "full_name": "Ananya Krishnan",
    "email": "ananya@example.com",
    "phone": "9876543210",
    "occupation": "Software Engineer",
    "annual_income_range": "₹25L – ₹50L",
    "primary_financial_goal": "Build a ₹2 Cr corpus by 40",
    "existing_investments": "PPF, some mutual funds",
    "risk_tolerance": "Medium",
    "key_concern": "Inflation eating into savings",
}

MOCK_CLASSIFICATION = {
    "segment": "Growth-Stage Professional",
    "risk_level": "Medium",
    "urgency": "Medium",
    "recommended_approach": "Focus on SIP-based equity allocation with an inflation hedge.",
    "confidence": 0.88,
    "reasoning": "Mid-career professional with clear corpus goal and moderate risk tolerance.",
    "proposed_new_fields": [],
    "success": True,
    "error": None,
}


def _seed_practitioner():
    p = Practitioner(email="test@example.com", name="Test Coach", vertical="financial_advisory")
    db.session.add(p)
    db.session.flush()
    return p


def test_webhook_creates_client(client, app, db_session):
    with app.app_context():
        p = _seed_practitioner()

        with patch("app.intake.routes.classify_intake") as mock_classify, \
             patch("app.intake.routes.sync_client_to_sheet"), \
             patch("app.intake.routes.ensure_sheet_headers"):

            from app.services.classification_service import ClassificationResult
            mock_classify.return_value = ClassificationResult(**{
                k: v for k, v in MOCK_CLASSIFICATION.items()
                if k in ClassificationResult.__dataclass_fields__
            })

            resp = client.post(
                "/intake/webhook",
                data=json.dumps(SAMPLE_INTAKE),
                content_type="application/json",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["segment"] == "Growth-Stage Professional"
        assert data["risk_level"] == "Medium"
        assert data["confidence"] == 0.88


def test_webhook_returns_500_without_practitioner(client, app, db_session):
    with app.app_context():
        # No practitioner seeded
        resp = client.post(
            "/intake/webhook",
            data=json.dumps(SAMPLE_INTAKE),
            content_type="application/json",
        )
        assert resp.status_code == 500


def test_intake_form_get(client, app, db_session):
    with app.app_context():
        _seed_practitioner()
        resp = client.get("/intake/form")
        assert resp.status_code == 200
        assert b"New Client Intake" in resp.data
