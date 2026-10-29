from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "vendor-service-insecure-dev-key-1234567890"),
    ENVIRONMENT=(str, "development"),
    POSTGRES_HOST=(str, "localhost"),
    POSTGRES_PORT=(int, 5432),
    VENDOR_DB_NAME=(str, "trustgrid_vendor"),
    VENDOR_DB_USER=(str, "vendor_user"),
    VENDOR_DB_PASSWORD=(str, "vendor_secure_pass_dev"),
    JWT_SECRET_KEY=(str, "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"),
    JWT_ALGORITHM=(str, "HS256"),
)

root_env = BASE_DIR.parent.parent / ".env"
if root_env.exists():
    environ.Env.read_env(root_env)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "vendors.apps.VendorsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("VENDOR_DB_NAME"),
        "USER": env("VENDOR_DB_USER"),
        "PASSWORD": env("VENDOR_DB_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "vendors.authentication.StatelessJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "vendors.permissions.IsTenantAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "vendors.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

JWT_SECRET_KEY = env("JWT_SECRET_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")

RABBITMQ_HOST = env("RABBITMQ_HOST", default="rabbitmq")
RABBITMQ_PORT = env.int("RABBITMQ_PORT", default=5672)
RABBITMQ_USER = env("RABBITMQ_USER", default="trustgrid_mq")
RABBITMQ_PASS = env("RABBITMQ_PASS", default="trustgrid_mq_pass_dev")
RABBITMQ_VHOST = env("RABBITMQ_VHOST", default="trustgrid_vhost")


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"