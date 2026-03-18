"""
Settings de PRODUÇÃO - Residencial Park Club
Funciona com DigitalOcean App Platform e Docker/VPS.
"""
import os
import dj_database_url
from .settings import *  # noqa

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "TROQUE-ESTA-CHAVE-EM-PRODUCAO")

ALLOWED_HOSTS = [
    "www.condominioparkclub.com.br",
    "condominioparkclub.com.br",
    ".ondigitalocean.app",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://www.condominioparkclub.com.br",
    "https://condominioparkclub.com.br",
    "https://*.ondigitalocean.app",
]

# Banco: usa DATABASE_URL (DigitalOcean App Platform) ou variáveis separadas (Docker)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "residencialparkclub"),
            "USER": os.environ.get("DB_USER", "enterprise_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "#otopodomundo2025"),
            "HOST": os.environ.get("DB_HOST", "db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

# WhiteNoise para servir static files (App Platform não tem Nginx)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# Static e media
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# Segurança HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
