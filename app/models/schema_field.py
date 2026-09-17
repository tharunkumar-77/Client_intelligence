import uuid
from datetime import datetime, timezone
from app.extensions import db


class SchemaField(db.Model):
    __tablename__ = "schema_fields"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    field_key = db.Column(db.String(100), nullable=False)   # snake_case key
    field_label = db.Column(db.String(255), nullable=False) # Human-readable
    field_type = db.Column(db.String(50), default="text")   # text | number | date | boolean
    confirmed = db.Column(db.Boolean, default=False)        # Practitioner confirmed
    proposed_by_response_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("practitioner_id", "field_key", name="uq_practitioner_field_key"),
    )

    practitioner = db.relationship("Practitioner", back_populates="schema_fields")

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "field_key": self.field_key,
            "field_label": self.field_label,
            "field_type": self.field_type,
            "confirmed": self.confirmed,
            "created_at": self.created_at.isoformat(),
        }
