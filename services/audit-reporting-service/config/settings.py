from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "insecure-audit-dev-key-change-in-production-1234567890"),
    ENVIRONMENT=(str, "development"),
    POSTGRES_HOST=(str, "localhost"),
    POSTGRES_PORT=(int, 5432),
    AUDIT_DB_NAME=(str, "trustgrid_audit"),
    AUDIT_DB_USER=(str, "audit_user"),
    AUDIT_DB_PASSWORD=(str, "audit_secure_pass_dev"),
    JWT_SECRET_KEY=(str, "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"),
    JWT_ALGORITHM=(str, "HS256"),
    JWT_EXPIRATION_SECONDS=(int, 3600),
    RABBITMQ_HOST=(str, "rabbitmq"),
    RABBITMQ_PORT=(int, 5672),
    RABBITMQ_USER=(str, "trustgrid_mq"),
    RABBITMQ_PASS=(str, "trustgrid_mq_pass_dev"),
    RABBITMQ_VHOST=(str, "trustgrid_vhost"),
)

root_env = BASE_DIR.parent.parent / ".env"
if root_env.exists():
    environ.Env.read_env(root_env)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "rest_framework",
    "django_filters",
    "audit.apps.AuditConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("AUDIT_DB_NAME"),
        "USER": env("AUDIT_DB_USER"),
        "PASSWORD": env("AUDIT_DB_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "audit.authentication.StatelessJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "audit.permissions.IsTenantAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 25,
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

JWT_SECRET_KEY = env("JWT_SECRET_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")
JWT_EXPIRATION_SECONDS = env("JWT_EXPIRATION_SECONDS")

RABBITMQ_HOST = env("RABBITMQ_HOST")
RABBITMQ_PORT = env("RABBITMQ_PORT")
RABBITMQ_USER = env("RABBITMQ_USER")
RABBITMQ_PASS = env("RABBITMQ_PASS")
RABBITMQ_VHOST = env("RABBITMQ_VHOST")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"