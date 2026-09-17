import uuid
from datetime import datetime, timezone
from app.extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    calendar_event_id = db.Column(db.String(255), nullable=True)
    meet_link = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="scheduled")  # scheduled | completed | cancelled
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    client = db.relationship("Client", back_populates="appointments")

    def __init__(self, **kwargs):
        super(Appointment, self).__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "practitioner_id": self.practitioner_id,
            "scheduled_at": self.scheduled_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "calendar_event_id": self.calendar_event_id,
            "meet_link": self.meet_link,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
