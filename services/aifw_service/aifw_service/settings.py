"""
Django settings for aifw-service Microservice.

Design decisions:
  - ALLOWED_HOSTS = ["*"]: This is an internal-only service (not Traefik-exposed).
    Docker container names with underscores (aifw_service) fail RFC 1034 hostname
    validation in Django's SecurityMiddleware/CommonMiddleware. Since the service
    is firewalled to the internal Docker network, wildcard is safe and correct.
  - MIDDLEWARE = []: SecurityMiddleware + CommonMiddleware both call request.get_host()
    which raises DisallowedHost for underscore hostnames. No middleware needed for
    an internal JSON API.
  - LLM API keys: passed through docker-compose environment — litellm reads them
    directly from os.environ, no re-assignment needed.
"""
import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Wildcard required: Docker container name 'aifw_service' contains underscore,
# which is rejected by RFC 1034 hostname validation in Django middleware.
# Safe because this service is not exposed via Traefik (internal network only).
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "aifw",
    "aifw.nl2sql",   # optional NL2SQL component — activates NL2SQLConfig + migrations
    "aifw_service",  # required for management command discovery (init_odoo_schema)
]

# Empty middleware: SecurityMiddleware and CommonMiddleware both call
# request.get_host() — this raises DisallowedHost for 'aifw_service:8001'
# even with ALLOWED_HOSTS=["*"] because of RFC 1034 underscore rejection.
MIDDLEWARE = []

ROOT_URLCONF = "aifw_service.urls"

WSGI_APPLICATION = "aifw_service.wsgi.application"

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Database ──────────────────────────────────────────────────────────────────────
# 'default': aifw own DB (LLMProvider, AIActionType, AIUsageLog, SchemaSource)
# 'odoo':    Odoo DB — read-only access via nl2sql_ro role for SQL execution
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("AIFW_DB_NAME", "aifw"),
        "USER": os.environ.get("AIFW_DB_USER", "aifw"),
        "PASSWORD": os.environ["AIFW_DB_PASSWORD"],
        "HOST": os.environ.get("AIFW_DB_HOST", "db"),
        "PORT": os.environ.get("AIFW_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    },
    "odoo": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("ODOO_DB_NAME", "odoo"),
        "USER": os.environ.get("ODOO_NL2SQL_USER", "nl2sql_user"),
        "PASSWORD": os.environ["ODOO_NL2SQL_PASSWORD"],
        "HOST": os.environ.get("ODOO_DB_HOST", "db"),
        "PORT": os.environ.get("ODOO_DB_PORT", "5432"),
        "CONN_MAX_AGE": 30,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "options": "-c default_transaction_read_only=on",
        },
    },
}

# ── Logging ────────────────────────────────────────────────────────────────────
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
        "LiteLLM": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
