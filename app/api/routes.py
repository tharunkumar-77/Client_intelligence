import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, render_template, session, url_for
from flask_login import current_user

from app.auth.routes import login_required
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.intake import IntakeResponse
from app.models.note import Reminder
from app.models.practitioner import Practitioner
from app.models.schema_field import SchemaField
from app.models.segment import Segment

api_bp = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


@api_bp.route("/")
def index():
    return redirect(url_for("api.dashboard"))


@api_bp.route("/dashboard")
@login_required
def dashboard():
    practitioner = current_user
    if not practitioner:
        return render_template("setup_required.html")

    clients = (
        Client.query.filter_by(practitioner_id=practitioner.id)
        .order_by(Client.created_at.desc())
        .all()
    )
    segments = Segment.query.filter_by(practitioner_id=practitioner.id).all()
    segment_counts = {
        seg.name: Client.query.filter_by(segment_id=seg.id).count()
        for seg in segments
    }

    now = datetime.now(timezone.utc)
    stats = {
        "total":         len(clients),
        "high_risk":     sum(1 for c in clients if c.risk_level == "High"),
        "high_urgency":  sum(1 for c in clients if c.urgency == "High"),
        "segments":      len(segments),
        "pending_reminders": Reminder.query.filter_by(
            practitioner_id=practitioner.id, resolved_at=None
        ).count(),
        "overdue_reminders": Reminder.query.filter(
            Reminder.practitioner_id == practitioner.id,
            Reminder.resolved_at.is_(None),
            Reminder.due_at < now,
        ).count(),
    }

    recent_intakes = (
        IntakeResponse.query.filter_by(practitioner_id=practitioner.id)
        .order_by(IntakeResponse.created_at.desc())
        .limit(5)
        .all()
    )

    # Pending AI-proposed schema fields for the confirmation banner
    pending_fields = (
        SchemaField.query
        .filter_by(practitioner_id=practitioner.id, confirmed=False)
        .order_by(SchemaField.created_at.asc())
        .all()
    )

    return render_template(
        "dashboard.html",
        practitioner=practitioner,
        clients=clients,
        segments=segments,
        segment_counts=segment_counts,
        stats=stats,
        recent_intakes=recent_intakes,
        pending_fields=pending_fields,
    )


@api_bp.route("/clients/<client_id>")
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    return render_template("client_detail.html", client=client)


@api_bp.route("/intake/responses")
@login_required
def intake_responses():
    practitioner = current_user
    responses = (
        IntakeResponse.query.filter_by(practitioner_id=practitioner.id)
        .order_by(IntakeResponse.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "intake_responses.html", responses=responses, practitioner=practitioner
    )


@api_bp.route("/audit")
@login_required
def audit_log():
    practitioner = current_user
    entries = (
        AuditLog.query.filter_by(practitioner_id=practitioner.id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return render_template("audit_log.html", entries=entries, practitioner=practitioner)


# ── JSON REST endpoints ──────────────────────────────────────────────────────

@api_bp.route("/api/clients")
@login_required
def api_clients():
    practitioner = current_user
    clients = Client.query.filter_by(practitioner_id=practitioner.id).all()
    return jsonify([c.to_dict() for c in clients])


@api_bp.route("/api/clients/<client_id>")
@login_required
def api_client(client_id):
    client = Client.query.get_or_404(client_id)
    return jsonify(client.to_dict())


@api_bp.route("/api/segments")
@login_required
def api_segments():
    practitioner = current_user
    segments = Segment.query.filter_by(practitioner_id=practitioner.id).all()
    return jsonify([s.to_dict() for s in segments])


@api_bp.route("/reminders")
@login_required
def reminders_page():
    practitioner = current_user
    return render_template("reminders.html", practitioner=practitioner)
