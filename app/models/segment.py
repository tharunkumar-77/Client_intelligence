import uuid
from datetime import datetime, timezone
from app.extensions import db


class Segment(db.Model):
    __tablename__ = "segments"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    ai_derived = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    practitioner = db.relationship("Practitioner", back_populates="segments")
    clients = db.relationship("Client", back_populates="segment", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "name": self.name,
            "description": self.description,
            "ai_derived": self.ai_derived,
            "created_at": self.created_at.isoformat(),
        }
