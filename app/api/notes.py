"""Phase 2 — Notes API routes"""
import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db, limiter, get_client_for_user
from app.models.client import Client
from app.models.note import Note
from app.services.audit_service import log_event
from app.services.note_service import process_note

notes_bp = Blueprint("notes", __name__)
logger = logging.getLogger(__name__)




@notes_bp.route("/clients/<client_id>/notes", methods=["GET"])
def list_notes(client_id):
    """Return all notes for a client, newest first."""
    client = get_client_for_user(client_id)
    notes = (
        Note.query
        .filter_by(client_id=client.id)
        .order_by(Note.created_at.desc())
        .limit(100)
        .all()
    )
    return jsonify([n.to_dict() for n in notes])


@notes_bp.route("/clients/<client_id>/notes", methods=["POST"])
@limiter.limit("10 per minute")
def add_note(client_id):
    """
    POST { "text": "..." }
    Returns the extracted NoteResult JSON.
    """
    client = get_client_for_user(client_id)
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner configured."}), 500

    body = request.get_json(silent=True) or {}
    raw_text = (body.get("text") or "").strip()
    if not raw_text:
        return jsonify({"error": "Note text is required."}), 400

    result = process_note(client, raw_text, practitioner.id)

    log_event(
        action="note_processed",
        actor="ai",
        practitioner_id=practitioner.id,
        client_id=client.id,
        payload={"note_id": result.note_id, "sentiment": result.sentiment,
                 "action_items_count": len(result.action_items), "success": result.success},
    )

    status = 200 if result.success else 500
    return jsonify(result.to_dict()), status
