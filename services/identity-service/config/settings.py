import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "insecure-dev-key-change-in-production-1234567890"),
    ENVIRONMENT=(str, "development"),
    POSTGRES_HOST=(str, "localhost"),
    POSTGRES_PORT=(int, 5432),
    IDENTITY_DB_NAME=(str, "trustgrid_identity"),
    IDENTITY_DB_USER=(str, "identity_user"),
    IDENTITY_DB_PASSWORD=(str, "identity_secure_pass_dev"),
    JWT_SECRET_KEY=(str, "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"),
    JWT_ALGORITHM=(str, "HS256"),
    JWT_EXPIRATION_SECONDS=(int, 3600),
)

# Read root .env file if it exists
root_env = BASE_DIR.parent.parent / ".env"
if root_env.exists():
    environ.Env.read_env(root_env)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "identity.apps.IdentityConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("IDENTITY_DB_NAME"),
        "USER": env("IDENTITY_DB_USER"),
        "PASSWORD": env("IDENTITY_DB_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "identity.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "identity.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

JWT_SECRET_KEY = env("JWT_SECRET_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")
JWT_EXPIRATION_SECONDS = env("JWT_EXPIRATION_SECONDS")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
