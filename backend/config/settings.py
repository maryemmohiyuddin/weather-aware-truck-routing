import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ON_VERCEL = os.environ.get("VERCEL") == "1"

# Placeholder for local runs and the Vercel demo. Not a secret.
# Set SECRET_KEY in the environment before storing sessions or accounts.
SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-not-a-secret"
_debug_default = "false" if ON_VERCEL else "true"
DEBUG = os.environ.get("DEBUG", _debug_default).lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
if ON_VERCEL:
    for host in (".vercel.app", ".now.sh", os.environ.get("VERCEL_URL", "")):
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "planner",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
if not ON_VERCEL:
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Nothing queries the database. Django still wants a DATABASES entry.
# On Vercel the disk is read-only outside /tmp, so the file lives there.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/tmp/db.sqlite3" if ON_VERCEL else BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
if not ON_VERCEL:
    STATIC_ROOT = BASE_DIR / "staticfiles"
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

_local_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_configured = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://[\w.-]+\.vercel\.app$"]
if _configured == ["*"]:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = list(dict.fromkeys(_local_origins + _configured))
