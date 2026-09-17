import uuid
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class Practitioner(UserMixin, db.Model):
    __tablename__ = "practitioners"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    vertical = db.Column(db.String(100), nullable=False, default="financial_advisory")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    clients = db.relationship("Client", back_populates="practitioner", lazy="dynamic")
    segments = db.relationship("Segment", back_populates="practitioner", lazy="dynamic")
    intake_responses = db.relationship("IntakeResponse", back_populates="practitioner", lazy="dynamic")
    notes = db.relationship("Note", back_populates="practitioner", lazy="dynamic")
    schema_fields = db.relationship("SchemaField", back_populates="practitioner", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "vertical": self.vertical,
            "created_at": self.created_at.isoformat(),
        }
