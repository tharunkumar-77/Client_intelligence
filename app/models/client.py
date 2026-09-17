import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.extensions import db


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    segment_id = db.Column(db.String(36), db.ForeignKey("segments.id"), nullable=True)
    status = db.Column(db.String(50), default="active")  # active | inactive
    risk_level = db.Column(db.String(20))  # Low | Medium | High
    urgency = db.Column(db.String(20))    # Low | Medium | High
    attributes = db.Column(JSONB, default=dict)  # Dynamic schema fields
    embedding   = db.Column(Vector(768), nullable=True)  # Gemini text-embedding-004
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    practitioner = db.relationship("Practitioner", back_populates="clients")
    segment = db.relationship("Segment", back_populates="clients")
    notes = db.relationship("Note", back_populates="client", lazy="dynamic")
    appointments = db.relationship("Appointment", back_populates="client", lazy="dynamic")
    queries = db.relationship("ClientQuery", back_populates="client", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "segment": self.segment.name if self.segment else None,
            "segment_id": self.segment_id,
            "status": self.status,
            "risk_level": self.risk_level,
            "urgency": self.urgency,
            "attributes": self.attributes or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    estimated_priority = db.Column(db.String(20))  # Low | Medium | High
    attributes = db.Column(JSONB, default=dict)
    intake_response_id = db.Column(db.String(36), db.ForeignKey("intake_responses.id"), nullable=True)
    converted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    converted_client_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "estimated_priority": self.estimated_priority,
            "attributes": self.attributes or {},
            "converted_at": self.converted_at.isoformat() if self.converted_at else None,
            "created_at": self.created_at.isoformat(),
        }
