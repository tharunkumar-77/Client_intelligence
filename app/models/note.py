import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.extensions import db


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    raw_input = db.Column(db.Text, nullable=False)
    structured_output = db.Column(JSONB, nullable=True)
    input_type  = db.Column(db.String(20), default="text")  # text | voice
    embedding   = db.Column(Vector(768), nullable=True)      # Gemini text-embedding-004
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    client = db.relationship("Client", back_populates="notes")
    practitioner = db.relationship("Practitioner", back_populates="notes")
    reminders = db.relationship("Reminder", back_populates="note", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "practitioner_id": self.practitioner_id,
            "raw_input": self.raw_input,
            "structured_output": self.structured_output,
            "input_type": self.input_type,
            "created_at": self.created_at.isoformat(),
        }


class Reminder(db.Model):
    __tablename__ = "reminders"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    note_id = db.Column(db.String(36), db.ForeignKey("notes.id"), nullable=True)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False)
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False)
    due_at = db.Column(db.DateTime(timezone=True), nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    note = db.relationship("Note", back_populates="reminders")

    def to_dict(self):
        return {
            "id": self.id,
            "note_id": self.note_id,
            "client_id": self.client_id,
            "practitioner_id": self.practitioner_id,
            "due_at": self.due_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }
