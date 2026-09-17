import logging

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from app.auth.routes import login_required
from app.extensions import db
from app.models.client import Lead
from app.models.practitioner import Practitioner
from app.services.triage_service import rank_leads

triage_bp = Blueprint("triage", __name__)
logger = logging.getLogger(__name__)


@triage_bp.route("/triage")
@login_required
def triage_view():
    practitioner = current_user
    if not practitioner:
        return render_template("setup_required.html")
    leads = Lead.query.filter_by(practitioner_id=practitioner.id, converted_at=None).all()
    ranked = rank_leads(leads)
    return render_template("triage.html", leads=ranked, practitioner=practitioner)


@triage_bp.route("/api/triage/leads")
@login_required
def api_leads_ranked():
    practitioner = current_user
    if not practitioner:
        return jsonify([])
    leads = Lead.query.filter_by(practitioner_id=practitioner.id, converted_at=None).all()
    return jsonify(rank_leads(leads))


@triage_bp.route("/api/triage/leads/<lead_id>/convert", methods=["POST"])
def convert_lead(lead_id):
    from app.models.client import Client
    from app.models.segment import Segment
    from datetime import datetime, timezone
    import uuid

    lead = Lead.query.get_or_404(lead_id)
    practitioner = current_user

    body = request.get_json(silent=True) or {}
    seg_name = body.get("segment", "Unclassified")
    seg = Segment.query.filter_by(practitioner_id=practitioner.id, name=seg_name).first()
    if not seg:
        seg = Segment(practitioner_id=practitioner.id, name=seg_name, ai_derived=False)
        db.session.add(seg)
        db.session.flush()

    client = Client(
        practitioner_id=practitioner.id,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        segment_id=seg.id,
        status="active",
        attributes=lead.attributes or {},
    )
    db.session.add(client)
    db.session.flush()

    lead.converted_at = datetime.now(timezone.utc)
    lead.converted_client_id = client.id
    db.session.commit()

    return jsonify({"client_id": client.id, "lead_id": lead.id}), 200
