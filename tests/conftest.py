import pytest
import os

os.environ["FLASK_ENV"] = "testing"
os.environ["DATABASE_URL"] = "postgresql://ci_user:ci_password@localhost:5432/ci_test"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["LLM_PROVIDER"] = "gemini"

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("development")
    app.config.update({
        "TESTING": True,
        "DATABASE_URL": "postgresql://ci_user:ci_password@localhost:5432/ci_test",
        "SQLALCHEMY_DATABASE_URI": "postgresql://ci_user:ci_password@localhost:5432/ci_test",
        "INTAKE_WEBHOOK_SECRET": "",  # disable sig check in tests
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def db_session(app):
    """Wrap each test in a transaction that rolls back afterward."""
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        _db.session.bind = connection
        yield _db.session
        _db.session.remove()
        transaction.rollback()
        connection.close()
