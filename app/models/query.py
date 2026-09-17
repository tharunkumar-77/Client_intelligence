import uuid
from datetime import datetime, timezone
from app.extensions import db


class ClientQuery(db.Model):
    __tablename__ = "client_queries"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=True)
    escalated = db.Column(db.Boolean, default=True)  # Always escalate by default
    escalation_reason = db.Column(db.Text, nullable=True)
    practitioner_response = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    client = db.relationship("Client", back_populates="queries")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "practitioner_id": self.practitioner_id,
            "question": self.question,
            "ai_response": self.ai_response,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
            "practitioner_response": self.practitioner_response,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat(),
        }
