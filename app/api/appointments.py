"""
Phase 13 — Appointment Scheduling API
Full CRUD + list/calendar endpoints for the Appointment model.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user

from app.auth.routes import login_required
from app.extensions import db, get_client_for_user
from app.models.appointment import Appointment
from app.models.client import Client
from app.services.audit_service import log_event

appointments_bp = Blueprint("appointments", __name__)
logger = logging.getLogger(__name__)


# ── Calendar page ─────────────────────────────────────────────────────────────

@appointments_bp.route("/appointments")
@login_required
def appointments_page():
    practitioner = current_user
    return render_template("appointments.html", practitioner=practitioner)


# ── List all appointments for practitioner ─────────────────────────────────────

@appointments_bp.route("/api/appointments")
@login_required
def list_appointments():
    """
    GET /api/appointments
    ?status=scheduled|completed|cancelled   (optional filter)
    ?client_id=<id>                         (optional)
    Returns list ordered by scheduled_at asc.
    """
    practitioner = current_user
    if not practitioner:
        return jsonify([])

    q = (
        Appointment.query
        .join(Client, Appointment.client_id == Client.id)
        .filter(Client.practitioner_id == practitioner.id)
    )

    status = request.args.get("status")
    if status:
        q = q.filter(Appointment.status == status)

    client_id = request.args.get("client_id")
    if client_id:
        q = q.filter(Appointment.client_id == client_id)

    appts = q.order_by(Appointment.scheduled_at.asc()).limit(100).all()

    result = []
    for a in appts:
        d = a.to_dict()
        # Enrich with client name for calendar display
        d["client_name"] = a.client.name if a.client else "—"
        result.append(d)

    return jsonify(result)


# ── Create appointment ────────────────────────────────────────────────────────

@appointments_bp.route("/api/clients/<client_id>/appointments", methods=["POST"])
@login_required
def create_appointment(client_id):
    """
    POST /api/clients/<id>/appointments
    Body: { scheduled_at, duration_minutes?, meet_link?, status? }
    """
    client = get_client_for_user(client_id)
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner"}), 500

    body = request.get_json(silent=True) or {}

    scheduled_at_str = body.get("scheduled_at")
    if not scheduled_at_str:
        return jsonify({"error": "scheduled_at is required (ISO 8601)"}), 400

    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
    except ValueError:
        return jsonify({"error": "Invalid scheduled_at format. Use ISO 8601."}), 400

    duration = int(body.get("duration_minutes", 60))
    duration = max(1, min(1440, duration))
    status = body.get("status", "scheduled")
    if status not in ("scheduled", "completed", "cancelled"):
        status = "scheduled"

    appt = Appointment(
        client_id=client.id,
        practitioner_id=practitioner.id,
        scheduled_at=scheduled_at,
        duration_minutes=duration,
        meet_link=body.get("meet_link") or None,
        status=status,
    )
    db.session.add(appt)
    db.session.commit()

    log_event(
        action="appointment_created",
        actor="practitioner",
        practitioner_id=practitioner.id,
        client_id=client.id,
        payload={"appointment_id": appt.id, "scheduled_at": scheduled_at_str},
    )

    d = appt.to_dict()
    d["client_name"] = client.name
    return jsonify(d), 201


# ── Update appointment ────────────────────────────────────────────────────────

@appointments_bp.route("/api/appointments/<appointment_id>", methods=["PATCH"])
@login_required
def update_appointment(appointment_id):
    """
    PATCH /api/appointments/<id>
    Body: { scheduled_at?, duration_minutes?, meet_link?, status? }
    """
    from flask import abort
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.practitioner_id != current_user.id:
        abort(404)
    body = request.get_json(silent=True) or {}

    if "scheduled_at" in body:
        try:
            appt.scheduled_at = datetime.fromisoformat(body["scheduled_at"].replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid scheduled_at"}), 400

    if "duration_minutes" in body:
        appt.duration_minutes = int(body["duration_minutes"])
    if "meet_link" in body:
        appt.meet_link = body["meet_link"] or None
    if "status" in body and body["status"] in ("scheduled", "completed", "cancelled"):
        appt.status = body["status"]

    db.session.commit()

    d = appt.to_dict()
    d["client_name"] = appt.client.name if appt.client else "—"
    return jsonify(d), 200


# ── Delete appointment ────────────────────────────────────────────────────────

@appointments_bp.route("/api/appointments/<appointment_id>", methods=["DELETE"])
@login_required
def delete_appointment(appointment_id):
    from flask import abort
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.practitioner_id != current_user.id:
        abort(404)
    db.session.delete(appt)
    db.session.commit()
    return jsonify({"deleted": appointment_id}), 200


# ── Client appointments list ──────────────────────────────────────────────────

@appointments_bp.route("/api/clients/<client_id>/appointments", methods=["GET"])
@login_required
def client_appointments(client_id):
    client = get_client_for_user(client_id)
    appts = (
        Appointment.query
        .filter_by(client_id=client.id)
        .order_by(Appointment.scheduled_at.asc())
        .limit(100)
        .all()
    )
    return jsonify([a.to_dict() for a in appts])
