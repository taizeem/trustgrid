import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "insecure-billing-dev-key-change-in-production-1234567890"),
    ENVIRONMENT=(str, "development"),
    POSTGRES_HOST=(str, "localhost"),
    POSTGRES_PORT=(int, 5432),
    BILLING_DB_NAME=(str, "trustgrid_billing"),
    BILLING_DB_USER=(str, "billing_user"),
    BILLING_DB_PASSWORD=(str, "billing_secure_pass_dev"),
    JWT_SECRET_KEY=(str, "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"),
    JWT_ALGORITHM=(str, "HS256"),
    JWT_EXPIRATION_SECONDS=(int, 3600),
    STRIPE_SECRET_KEY=(str, "sk_test_mock_sandbox_key_123"),
    STRIPE_WEBHOOK_SECRET=(str, "whsec_mock_sandbox_secret_456"),
    PAYMENT_SANDBOX_MODE=(bool, True),
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
    "billing.apps.BillingConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("BILLING_DB_NAME"),
        "USER": env("BILLING_DB_USER"),
        "PASSWORD": env("BILLING_DB_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "billing.authentication.StatelessJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "billing.permissions.IsTenantAuthenticated",
    ),
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

JWT_SECRET_KEY = env("JWT_SECRET_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")
JWT_EXPIRATION_SECONDS = env("JWT_EXPIRATION_SECONDS")

STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET")
PAYMENT_SANDBOX_MODE = env("PAYMENT_SANDBOX_MODE")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"