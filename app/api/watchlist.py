"""
Phase 14 — Watchlist API
Create named watchlists, add/remove clients, list members.
"""
import logging

from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user
from flask import abort

from app.auth.routes import login_required
from app.extensions import db, get_client_for_user
from app.models.client import Client
from app.models.watchlist import Watchlist

watchlist_bp = Blueprint("watchlist", __name__)
logger = logging.getLogger(__name__)


@watchlist_bp.route("/watchlist")
@login_required
def watchlist_page():
    practitioner = current_user
    return render_template("watchlist.html", practitioner=practitioner)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@watchlist_bp.route("/api/watchlists", methods=["GET"])
@login_required
def list_watchlists():
    practitioner = current_user
    if not practitioner:
        return jsonify([])
    wls = Watchlist.query.filter_by(practitioner_id=practitioner.id).all()
    result = []
    for w in wls:
        d = w.to_dict()
        d["client_count"] = w.clients.count()
        result.append(d)
    return jsonify(result)


@watchlist_bp.route("/api/watchlists", methods=["POST"])
@login_required
def create_watchlist():
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner"}), 500
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    wl = Watchlist(
        practitioner_id=practitioner.id,
        name=name,
        description=body.get("description") or "",
    )
    db.session.add(wl)
    db.session.commit()
    d = wl.to_dict()
    d["client_count"] = 0
    return jsonify(d), 201


@watchlist_bp.route("/api/watchlists/<wl_id>", methods=["DELETE"])
@login_required
def delete_watchlist(wl_id):
    wl = Watchlist.query.get_or_404(wl_id)
    if wl.practitioner_id != current_user.id:
        abort(404)
    db.session.delete(wl)
    db.session.commit()
    return jsonify({"deleted": wl_id}), 200


# ── Members ───────────────────────────────────────────────────────────────────

@watchlist_bp.route("/api/watchlists/<wl_id>/clients", methods=["GET"])
@login_required
def watchlist_clients(wl_id):
    wl = Watchlist.query.get_or_404(wl_id)
    if wl.practitioner_id != current_user.id:
        abort(404)
    return jsonify([c.to_dict() for c in wl.clients.limit(100).all()])


@watchlist_bp.route("/api/watchlists/<wl_id>/clients/<client_id>", methods=["POST"])
@login_required
def add_to_watchlist(wl_id, client_id):
    wl     = Watchlist.query.get_or_404(wl_id)
    if wl.practitioner_id != current_user.id:
        abort(404)
    client = get_client_for_user(client_id)
    if client not in wl.clients.all():
        wl.clients.append(client)
        db.session.commit()
    return jsonify({"added": client_id}), 200


@watchlist_bp.route("/api/watchlists/<wl_id>/clients/<client_id>", methods=["DELETE"])
@login_required
def remove_from_watchlist(wl_id, client_id):
    wl     = Watchlist.query.get_or_404(wl_id)
    if wl.practitioner_id != current_user.id:
        abort(404)
    client = get_client_for_user(client_id)
    if client in wl.clients.all():
        wl.clients.remove(client)
        db.session.commit()
    return jsonify({"removed": client_id}), 200


# ── Quick-flag: which watchlists contain a given client ───────────────────────

@watchlist_bp.route("/api/clients/<client_id>/watchlists", methods=["GET"])
@login_required
def client_watchlists(client_id):
    # Verify client ownership
    client = get_client_for_user(client_id)
    practitioner = current_user
    if not practitioner:
        return jsonify([])
    all_wls = Watchlist.query.filter_by(practitioner_id=practitioner.id).all()
    result = []
    for wl in all_wls:
        d = wl.to_dict()
        d["contains_client"] = any(c.id == client_id for c in wl.clients.all())
        result.append(d)
    return jsonify(result)
