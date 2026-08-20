"""Settings usados APENAS pela suite de testes (nunca em producao).

Reaproveita o settings de desenvolvimento e troca o banco por sqlite em memoria,
para rodar `manage.py test --settings=parkclub.settings_test` sem depender do
PostgreSQL local. A producao continua usando parkclub.settings_prod via .env.
"""

import tempfile

from parkclub.settings import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["*"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
MEDIA_ROOT = tempfile.mkdtemp()
