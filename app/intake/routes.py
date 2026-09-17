import hmac
import hashlib
import logging
from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from app.extensions import db, limiter
from app.models.client import Client
from app.models.intake import IntakeResponse
from app.models.practitioner import Practitioner
from app.models.segment import Segment
from app.services.audit_service import log_event
from app.services.classification_service import ClassificationResult, classify_intake
from app.services.sheets_sync import ensure_sheet_headers, sync_client_to_sheet
from app.vertical.loader import load_vertical_config

intake_bp = Blueprint("intake", __name__)
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def resolve_practitioner(data=None) -> Practitioner:
    """Resolve practitioner for multi-tenant intake/webhook."""
    from flask_login import current_user
    if current_user and current_user.is_authenticated:
        return current_user
    
    pid = request.args.get("pid")
    if not pid and data:
        pid = data.get("practitioner_id")
    if pid:
        return Practitioner.query.get(pid)
        
    return Practitioner.query.first()


def _verify_signature(payload: bytes, header_sig: str) -> bool:
    secret = current_app.config.get("INTAKE_WEBHOOK_SECRET", "")
    if not secret:
        return True  # skip verification in dev when no secret is set
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig or "")


def _find_or_create_segment(practitioner_id: str, name: str) -> Segment:
    seg = Segment.query.filter_by(practitioner_id=practitioner_id, name=name.strip()).first()
    if not seg:
        seg = Segment(practitioner_id=practitioner_id, name=name.strip(), ai_derived=True)
        db.session.add(seg)
        db.session.flush()
    return seg


def _upsert_client(practitioner: Practitioner, data: dict, result: ClassificationResult, segment: Segment) -> Client:
    email = (data.get("email") or "").strip().lower() or None
    name = data.get("full_name") or data.get("name") or "Unknown"
    phone = data.get("phone") or None

    base_keys = {"full_name", "name", "email", "phone"}
    attributes = {k: v for k, v in data.items() if k not in base_keys and not k.startswith("_")}

    client = Client.query.filter_by(practitioner_id=practitioner.id, email=email).first() if email else None

    if client:
        client.segment_id = segment.id
        client.risk_level = result.risk_level
        client.urgency = result.urgency
        if phone:
            client.phone = phone
        existing = client.attributes or {}
        existing.update(attributes)
        client.attributes = existing
    else:
        client = Client(
            practitioner_id=practitioner.id,
            name=name,
            email=email,
            phone=phone,
            segment_id=segment.id,
            risk_level=result.risk_level,
            urgency=result.urgency,
            status="active",
            attributes=attributes,
        )
        db.session.add(client)
        db.session.flush()

    # ── Generate/refresh embedding (non-fatal) ────────────────────────────
    try:
        from app.services.embedding_service import embed_client
        vec = embed_client(client)
        if vec:
            client.embedding = vec
    except Exception as emb_exc:
        logger.warning("Client embedding failed (non-fatal): %s", emb_exc)

    return client


# ── Routes ─────────────────────────────────────────────────────────────────────

@intake_bp.route("/webhook", methods=["POST"])
@limiter.limit("5 per minute")
def webhook():
    """
    Receives a new intake submission from Google Forms (via Apps Script) or the native form.
    Pipeline: validate → store raw → classify → upsert client → audit → sync to Sheets.
    """
    raw_body = request.get_data()
    if not _verify_signature(raw_body, request.headers.get("X-Intake-Signature", "")):
        logger.warning("Webhook signature mismatch — request rejected.")
        abort(401, "Invalid signature.")

    data: dict = request.get_json(force=True, silent=True) or {}
    email = str(data.get("email") or "").strip()
    name = str(data.get("full_name") or data.get("name") or "").strip()
    
    if not email or not name:
        return jsonify({"error": "Validation failed: 'email' and 'name' are required fields."}), 400

    practitioner = resolve_practitioner(data)

    if not practitioner:
        return jsonify({"error": "No practitioner configured. Run: python scripts/seed.py"}), 500

    source = data.pop("_source", "native_form")

    # 1 — Persist raw intake
    intake = IntakeResponse(
        practitioner_id=practitioner.id,
        raw_json=data,
        source=source,
    )
    db.session.add(intake)
    db.session.flush()

    # 2 — Classify with vertical config
    try:
        vc = load_vertical_config(practitioner.vertical)
        result = classify_intake(data, vc)
    except Exception as exc:
        logger.exception("Classification pipeline error")
        intake.processing_error = str(exc)
        db.session.commit()
        return jsonify({"error": "Classification failed.", "detail": str(exc)}), 500

    # 3 — Persist classification result
    intake.classification_result = result.to_dict()
    intake.processed_at = datetime.now(timezone.utc)

    # 4 — Segment + client upsert
    segment = _find_or_create_segment(practitioner.id, result.segment)
    client = _upsert_client(practitioner, data, result, segment)
    intake.client_id = client.id

    db.session.commit()

    # 5 — Audit log
    log_event(
        action="intake_classified",
        actor="ai",
        practitioner_id=practitioner.id,
        client_id=client.id,
        payload={
            "intake_id": intake.id,
            "segment": result.segment,
            "risk_level": result.risk_level,
            "urgency": result.urgency,
            "confidence": result.confidence,
            "proposed_new_fields_count": len(result.proposed_new_fields),
        },
    )

    # 6 — Sheets sync (non-fatal if unconfigured)
    ensure_sheet_headers()
    sync_client_to_sheet(client)

    logger.info(
        f"Intake processed | client={client.name} | segment={result.segment} "
        f"| risk={result.risk_level} | confidence={result.confidence:.2f}"
    )
    return jsonify({
        "status": "ok",
        "client_id": client.id,
        "segment": result.segment,
        "risk_level": result.risk_level,
        "urgency": result.urgency,
        "confidence": result.confidence,
        "proposed_new_fields": [
            {"key": f.key, "label": f.label} for f in result.proposed_new_fields
        ],
    }), 200


@intake_bp.route("/form", methods=["GET"])
def intake_form():
    """Native web intake form — for local dev and testing."""
    practitioner = resolve_practitioner()
    if not practitioner:
        return "No practitioner configured. Run: python scripts/seed.py", 500
    vc = load_vertical_config(practitioner.vertical)
    return render_template("intake_form.html", questions=vc.intake_questions, practitioner=practitioner, vc=vc)


@intake_bp.route("/form", methods=["POST"])
@limiter.limit("5 per minute")
def intake_form_submit():
    """Handle native form POST — normalise to JSON then reuse the webhook pipeline."""
    form_data = request.form.to_dict()
    email = str(form_data.get("email") or "").strip()
    name = str(form_data.get("full_name") or form_data.get("name") or "").strip()
    
    if not email or not name:
        practitioner = resolve_practitioner(form_data)
        vc = load_vertical_config(practitioner.vertical) if practitioner else None
        return render_template("intake_form.html", questions=vc.intake_questions if vc else [], practitioner=practitioner, vc=vc, error="Name and Email are required."), 400

    form_data["_source"] = "native_form"

    # Monkey-patch get_json for the webhook handler reuse
    with current_app.test_request_context(
        "/intake/webhook",
        method="POST",
        json=form_data,
        headers={"Content-Type": "application/json"},
    ):
        from flask import request as inner_request
        # Instead of duplicating, we call the pipeline directly via the service layer
        pass

    # Simpler: just POST to the webhook inline
    practitioner = resolve_practitioner(form_data)
    if not practitioner:
        return "No practitioner configured.", 500

    data = {k: v for k, v in form_data.items()}
    source = data.pop("_source", "native_form")

    vc = load_vertical_config(practitioner.vertical)

    intake = IntakeResponse(practitioner_id=practitioner.id, raw_json=data, source=source)
    db.session.add(intake)
    db.session.flush()

    try:
        result = classify_intake(data, vc)
    except Exception as exc:
        intake.processing_error = str(exc)
        db.session.commit()
        return render_template("intake_form.html", questions=vc.intake_questions, practitioner=practitioner,
                               vc=vc, error=str(exc)), 500

    intake.classification_result = result.to_dict()
    intake.processed_at = datetime.now(timezone.utc)
    segment = _find_or_create_segment(practitioner.id, result.segment)
    client = _upsert_client(practitioner, data, result, segment)
    intake.client_id = client.id
    db.session.commit()

    log_event(action="intake_classified", actor="ai",
              practitioner_id=practitioner.id, client_id=client.id,
              payload={"intake_id": intake.id, "segment": result.segment,
                       "confidence": result.confidence})
    ensure_sheet_headers()
    sync_client_to_sheet(client)

    return render_template("intake_success.html", client=client, result=result, practitioner=practitioner)
