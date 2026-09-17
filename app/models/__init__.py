# Models package — all models imported in app factory to register with SQLAlchemy
from app.models.practitioner import Practitioner
from app.models.client import Client
from app.models.segment import Segment
from app.models.intake import IntakeResponse
from app.models.schema_field import SchemaField
from app.models.note import Note, Reminder
from app.models.appointment import Appointment
from app.models.query import ClientQuery
from app.models.watchlist import Watchlist, watchlist_clients
from app.models.audit import AuditLog
