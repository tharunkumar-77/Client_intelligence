import uuid
from datetime import datetime, timezone
from app.extensions import db

# Association table
watchlist_clients = db.Table(
    "watchlist_clients",
    db.Column("watchlist_id", db.String(36), db.ForeignKey("watchlists.id"), primary_key=True),
    db.Column("client_id", db.String(36), db.ForeignKey("clients.id"), primary_key=True),
    db.Column("added_at", db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)


class Watchlist(db.Model):
    __tablename__ = "watchlists"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    practitioner_id = db.Column(db.String(36), db.ForeignKey("practitioners.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    clients = db.relationship("Client", secondary=watchlist_clients, lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "practitioner_id": self.practitioner_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }
