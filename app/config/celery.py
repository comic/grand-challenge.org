import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("grandchallenge")
app.config_from_object("django.conf:settings", namespace="CELERY_")
# Load all of the tasks from the registered apps
app.autodiscover_tasks()
