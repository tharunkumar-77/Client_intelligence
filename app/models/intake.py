import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class IntakeResponse(db.Model):
    __tablename__ = "intake_responses"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    raw_json = db.Column(JSONB, nullable=False)
    source = db.Column(db.String(50), default="native_form")  # native_form | google_forms
    classification_result = db.Column(JSONB, nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=True)
    processing_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    practitioner = db.relationship("Practitioner", back_populates="intake_responses")

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "raw_json": self.raw_json,
            "source": self.source,
            "classification_result": self.classification_result,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "client_id": self.client_id,
            "processing_error": self.processing_error,
            "created_at": self.created_at.isoformat(),
        }
