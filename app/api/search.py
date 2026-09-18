"""
Phase 10 — Semantic search, CSV export, and client profile editing.
"""
import csv
import io
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, make_response, request
from flask_login import current_user
from flask import abort

from app.auth.routes import login_required
from app.extensions import db, get_client_for_user
from app.models.client import Client
from app.services.embedding_service import backfill_embeddings, semantic_search

search_bp = Blueprint("search", __name__)
logger = logging.getLogger(__name__)


# ── Semantic search ────────────────────────────────────────────────────────────

@search_bp.route("/api/search")
@login_required
def api_search():
    """
    GET /api/search?q=<natural language query>&limit=10
    Returns ranked clients by semantic similarity.
    """
    practitioner = current_user
    if not practitioner:
        return jsonify([])

    query = (request.args.get("q") or "").strip()
    limit = min(int(request.args.get("limit", 10)), 30)

    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    results = semantic_search(query, practitioner.id, limit=limit)
    return jsonify(results)


# ── CSV export ─────────────────────────────────────────────────────────────────

@search_bp.route("/api/clients/export.csv")
@login_required
def export_clients_csv():
    """Download all clients as a CSV file."""
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner"}), 500

    clients = (
        Client.query
        .filter_by(practitioner_id=practitioner.id)
        .order_by(Client.created_at.desc())
        .limit(1000)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Email", "Phone", "Segment", "Risk Level",
        "Urgency", "Status", "Created", "Attributes"
    ])
    for c in clients:
        import json as _json
        writer.writerow([
            c.name,
            c.email or "",
            c.phone or "",
            c.segment.name if c.segment else "",
            c.risk_level or "",
            c.urgency or "",
            c.status,
            c.created_at.strftime("%Y-%m-%d"),
            _json.dumps(c.attributes or {}),
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="clients_{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    return response


# ── Client profile editing ─────────────────────────────────────────────────────

@search_bp.route("/api/clients/<client_id>", methods=["PATCH"])
@login_required
def update_client(client_id):
    """
    PATCH /api/clients/<id>
    Body: { name?, email?, phone?, status?, risk_level?, urgency?, attributes? }
    """
    client = get_client_for_user(client_id)
    body = request.get_json(silent=True) or {}

    allowed = {"name", "email", "phone", "status", "risk_level", "urgency"}
    for field in allowed:
        if field in body:
            setattr(client, field, body[field])

    if "attributes" in body and isinstance(body["attributes"], dict):
        existing = dict(client.attributes or {})
        existing.update(body["attributes"])
        client.attributes = existing

    client.updated_at = datetime.now(timezone.utc)

    # Refresh embedding after edit
    try:
        from app.services.embedding_service import embed_client
        vec = embed_client(client)
        if vec:
            client.embedding = vec
    except Exception:
        pass

    db.session.commit()
    return jsonify(client.to_dict()), 200


# ── Embedding backfill (admin utility) ────────────────────────────────────────

@search_bp.route("/api/admin/backfill-embeddings", methods=["POST"])
@login_required
def admin_backfill():
    """Backfill missing embeddings for all clients. Run once after upgrading."""
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner"}), 500
    count = backfill_embeddings(practitioner.id)
    return jsonify({"updated": count}), 200
