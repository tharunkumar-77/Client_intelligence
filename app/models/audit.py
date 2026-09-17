import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), nullable=True, index=True)
    client_id = db.Column(db.String(36), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)  # e.g. "intake_classified"
    actor = db.Column(db.String(50), nullable=False)    # "ai" | "practitioner" | "system"
    payload = db.Column(JSONB, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "client_id": self.client_id,
            "action": self.action,
            "actor": self.actor,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }
