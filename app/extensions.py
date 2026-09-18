from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
login_manager = LoginManager()


def get_client_for_user(client_id: str):
    from app.models.client import Client
    from flask_login import current_user
    from flask import abort
    client = Client.query.get_or_404(client_id)
    if client.practitioner_id != current_user.id:
        abort(404)
    return client
