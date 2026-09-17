import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    SHEETS_SPREADSHEET_ID = os.environ.get("SHEETS_SPREADSHEET_ID")
    INTAKE_WEBHOOK_SECRET = os.environ.get("INTAKE_WEBHOOK_SECRET", "")
    DEFAULT_VERTICAL = os.environ.get("DEFAULT_VERTICAL", "financial_advisory")
    SESSION_COOKIE_HTTPONLY = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://ci_user:ci_password@localhost:5432/client_intelligence",
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    
    # Render provides 'postgres://' but SQLAlchemy requires 'postgresql://'
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = db_url
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
