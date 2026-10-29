import os

from celery import Celery


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

app = Celery("config")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

app.autodiscover_tasks()


import os
from urllib.parse import urlparse

redis_url = os.environ.get("REDIS_URL", "")
print("Redis URL scheme:", urlparse(redis_url).scheme)
print("Redis URL configured:", bool(redis_url))