import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from app.config import config_by_name
from app.extensions import db, migrate, limiter, login_manager


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "alert-error"

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from app.intake.routes import intake_bp
    from app.api.routes import api_bp
    from app.api.notes import notes_bp         # Phase 2
    from app.api.schema import schema_bp       # Phase 3
    from app.api.voice import voice_bp         # Phase 4
    from app.api.triage import triage_bp       # Phase 5
    from app.api.reminders import reminders_bp # Phase 6
    from app.api.queries import queries_bp     # Phase 7
    from app.auth.routes import auth_bp        # Phase 8
    from app.api.search import search_bp       # Phase 10
    from app.api.analytics import analytics_bp # Phase 11
    from app.api.appointments import appointments_bp # Phase 13
    from app.api.watchlist import watchlist_bp       # Phase 14
    from app.api.timeline import timeline_bp         # Phase 15

    app.register_blueprint(auth_bp)
    app.register_blueprint(intake_bp, url_prefix="/intake")
    app.register_blueprint(api_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(schema_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(triage_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(queries_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(timeline_bp)

    # Ensure models are imported so SQLAlchemy registers them
    with app.app_context():
        from app.models import (  # noqa: F401
            practitioner, client, segment, intake,
            schema_field, note, appointment, query,
            watchlist, audit
        )

    # ── Error handlers ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template as _rt
        return _rt("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template as _rt
        return _rt("500.html"), 500

    return app
