"""Phase 6 — Reminders API routes"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.models.note import Reminder
from app.models.practitioner import Practitioner

reminders_bp = Blueprint("reminders", __name__)
logger = logging.getLogger(__name__)


@reminders_bp.route("/reminders", methods=["GET"])
def list_reminders():
    """All unresolved reminders for the practitioner, sorted by due date."""
    practitioner = current_user
    if not practitioner:
        return jsonify([])

    only_pending = request.args.get("pending", "true").lower() == "true"
    q = Reminder.query.filter_by(practitioner_id=practitioner.id)
    if only_pending:
        q = q.filter(Reminder.resolved_at.is_(None))
    reminders = q.order_by(Reminder.due_at.asc()).limit(100).all()
    return jsonify([r.to_dict() for r in reminders])


@reminders_bp.route("/reminders/<reminder_id>/resolve", methods=["POST"])
def resolve_reminder(reminder_id):
    from flask import abort
    reminder = Reminder.query.get_or_404(reminder_id)
    if reminder.practitioner_id != current_user.id:
        abort(404)
    reminder.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(reminder.to_dict()), 200


@reminders_bp.route("/clients/<client_id>/reminders", methods=["GET"])
def client_reminders(client_id):
    from app.extensions import get_client_for_user
    client = get_client_for_user(client_id)
    reminders = (
        Reminder.query
        .filter_by(client_id=client.id)
        .order_by(Reminder.due_at.asc())
        .limit(100)
        .all()
    )
    return jsonify([r.to_dict() for r in reminders])
