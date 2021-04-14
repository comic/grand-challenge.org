import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

celery_app = Celery("grandchallenge")
celery_app.config_from_object("django.conf:settings", namespace="CELERY_")
celery_app.autodiscover_tasks()
