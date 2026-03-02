"""
Django settings for aifw-service Microservice.

Reads all sensitive config from environment variables.
Non-sensitive defaults are hardcoded for container deployment.
"""
import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "aifw",
    "aifw_service",
]

MIDDLEWARE = []

ROOT_URLCONF = "aifw_service.urls"

WSGI_APPLICATION = "aifw_service.wsgi.application"

# ── Database ────────────────────────────────────────────────────────────────
# Primary DB: aifw own DB for LLMProvider, AIActionType, AIUsageLog, SchemaSource
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("AIFW_DB_NAME", "aifw"),
        "USER": os.environ.get("AIFW_DB_USER", "aifw"),
        "PASSWORD": os.environ["AIFW_DB_PASSWORD"],
        "HOST": os.environ.get("AIFW_DB_HOST", "db"),
        "PORT": os.environ.get("AIFW_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    },
    # Odoo's PostgreSQL DB — used by SQLExecutor for NL2SQL queries (read-only via nl2sql_ro role)
    "odoo": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("ODOO_DB_NAME", "odoo"),
        "USER": os.environ.get("ODOO_NL2SQL_USER", "nl2sql_user"),
        "PASSWORD": os.environ["ODOO_NL2SQL_PASSWORD"],
        "HOST": os.environ.get("ODOO_DB_HOST", "db"),
        "PORT": os.environ.get("ODOO_DB_PORT", "5432"),
        "CONN_MAX_AGE": 30,
        "OPTIONS": {
            "options": "-c default_transaction_read_only=on",
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── LLM Provider API Keys (read by litellm via aifw.service) ────────────────
# Set whichever keys are available — aifw uses DB-configured provider routing.
if os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
if os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]

# ── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "aifw": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "aifw_service": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
