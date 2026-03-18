"""
Settings de PRODUÇÃO - Residencial Park Club
Herda tudo do settings base e sobrescreve o necessário.
"""
import os
from .settings import *  # noqa

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "TROQUE-ESTA-CHAVE-EM-PRODUCAO-use-algo-longo-e-aleatorio")

ALLOWED_HOSTS = [
    "www.condominioparkclub.com.br",
    "condominioparkclub.com.br",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://www.condominioparkclub.com.br",
    "https://condominioparkclub.com.br",
]

# Banco via Docker interno
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

# Static e media servidos pelo Nginx
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# Segurança HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Nginx cuida disso
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
