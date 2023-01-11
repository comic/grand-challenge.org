import logging
import os

from celery import Celery
from celery.concurrency.solo import TaskPool
from celery.exceptions import ImproperlyConfigured
from celery.signals import celeryd_after_setup
from django.conf import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

celery_app = Celery("grandchallenge")
celery_app.config_from_object("django.conf:settings", namespace="CELERY_")
celery_app.autodiscover_tasks()


@celeryd_after_setup.connect()
def check_configuration(*, instance, **__):
    if any(q in instance.app.amqp.queues for q in settings.CELERY_SOLO_QUEUES):
        if instance.concurrency != 1:
            raise ImproperlyConfigured("Worker concurrency must be 1")
        elif not isinstance(instance.pool, TaskPool):
            raise ImproperlyConfigured("Worker must use the solo task pool")
        elif not instance.task_events:
            raise ImproperlyConfigured("Worker must send task events")
        else:
            logger.info("Worker solo setup OK")
    else:
        logger.info("Worker setup OK")
