import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required when DJANGO_DEBUG is not 1")
    SECRET_KEY = "dev-only-insecure-key"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# Behind a TLS-terminating proxy (Railway, Render...) so absolute URLs such as map_url use https.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.gis",
    "rest_framework",
    "drf_spectacular",
    "fuel_route",
]

MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("DATABASE_NAME", ""),
        "USER": os.environ.get("DATABASE_USER", ""),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", ""),
        "HOST": os.environ.get("DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
    }
}

# Django only prints errors to the console when DEBUG is on; hosting platforms read stdout/stderr.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django": {"handlers": ["console"], "level": "WARNING"}},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "fuel_route.api.presenters.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

STATION_DATA_DIR = BASE_DIR / "data"

# External providers (free, no API key). One OSRM call per request; Nominatim only as fallback.
OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
NOMINATIM_URL = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
EXTERNAL_TIMEOUT_SECONDS = float(os.environ.get("EXTERNAL_TIMEOUT_SECONDS", "10"))
NOMINATIM_MIN_INTERVAL_SECONDS = 1.0  # usage policy: at most one request per second
HTTP_USER_AGENT = "fuel-route-optimizer/0.1 (assessment demo)"

# Corridor around the route: a station qualifies within base + its city radius (capped).
CORRIDOR_BASE_METERS = float(os.environ.get("CORRIDOR_BASE_METERS", "5000"))
CORRIDOR_RADIUS_CAP_METERS = float(os.environ.get("CORRIDOR_RADIUS_CAP_METERS", "10000"))

SPECTACULAR_SETTINGS = {
    "TITLE": "Fuel Route Optimizer API",
    "DESCRIPTION": "Cheapest fuel stops along a US driving route (500-mile range, 10 MPG).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
