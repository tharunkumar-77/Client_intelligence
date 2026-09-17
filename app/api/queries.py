"""Phase 7 — Client Query API routes"""
import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.models.client import Client
from app.models.practitioner import Practitioner
from app.models.query import ClientQuery
from app.services.audit_service import log_event
from app.services.query_service import process_query

queries_bp = Blueprint("queries", __name__)
logger = logging.getLogger(__name__)


@queries_bp.route("/clients/<client_id>/queries", methods=["GET"])
def list_queries(client_id):
    client = Client.query.get_or_404(client_id)
    queries = (
        ClientQuery.query
        .filter_by(client_id=client.id)
        .order_by(ClientQuery.created_at.desc())
        .all()
    )
    return jsonify([q.to_dict() for q in queries])


@queries_bp.route("/clients/<client_id>/queries", methods=["POST"])
def add_query(client_id):
    client = Client.query.get_or_404(client_id)
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner configured."}), 500

    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required."}), 400

    query = process_query(client, question, practitioner.id)

    log_event(
        action="query_submitted",
        actor="client",
        practitioner_id=practitioner.id,
        client_id=client.id,
        payload={"query_id": query.id, "escalated": query.escalated},
    )
    return jsonify(query.to_dict()), 200


@queries_bp.route("/clients/<client_id>/queries/<query_id>/respond", methods=["POST"])
def respond_query(client_id, query_id):
    """Practitioner submits a response to an escalated query."""
    from app.extensions import db
    from datetime import datetime, timezone

    query = ClientQuery.query.get_or_404(query_id)
    body = request.get_json(silent=True) or {}
    response_text = (body.get("response") or "").strip()
    if not response_text:
        return jsonify({"error": "response is required."}), 400

    query.practitioner_response = response_text
    query.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(query.to_dict()), 200
