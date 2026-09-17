"""Phase 3 — Dynamic Schema confirmation API"""
import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.models.practitioner import Practitioner
from app.models.schema_field import SchemaField

schema_bp = Blueprint("schema", __name__)
logger = logging.getLogger(__name__)


@schema_bp.route("/api/schema/pending", methods=["GET"])
def pending_fields():
    practitioner = current_user
    if not practitioner:
        return jsonify([])
    fields = (
        SchemaField.query
        .filter_by(practitioner_id=practitioner.id, confirmed=False)
        .order_by(SchemaField.created_at.asc())
        .all()
    )
    return jsonify([f.to_dict() for f in fields])


@schema_bp.route("/api/schema/<field_id>/confirm", methods=["POST"])
def confirm_field(field_id):
    sf = SchemaField.query.get_or_404(field_id)
    sf.confirmed = True
    db.session.commit()
    return jsonify(sf.to_dict()), 200


@schema_bp.route("/api/schema/<field_id>/reject", methods=["DELETE"])
def reject_field(field_id):
    sf = SchemaField.query.get_or_404(field_id)
    db.session.delete(sf)
    db.session.commit()
    return jsonify({"deleted": field_id}), 200


@schema_bp.route("/api/schema", methods=["GET"])
def confirmed_fields():
    practitioner = current_user
    if not practitioner:
        return jsonify([])
    fields = (
        SchemaField.query
        .filter_by(practitioner_id=practitioner.id, confirmed=True)
        .order_by(SchemaField.created_at.asc())
        .all()
    )
    return jsonify([f.to_dict() for f in fields])
