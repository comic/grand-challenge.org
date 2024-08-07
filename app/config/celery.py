import logging
import os
import platform
import resource
from math import ceil

import requests
from celery import Celery
from celery.exceptions import ImproperlyConfigured
from celery.signals import celeryd_after_setup, task_postrun, task_prerun
from django.conf import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

celery_app = Celery("grandchallenge")
celery_app.config_from_object("django.conf:settings", namespace="CELERY_")
celery_app.autodiscover_tasks()


@celeryd_after_setup.connect()
def check_configuration(*, instance, **__):
    """
    Check that the instance is configured correctly for a solo worker

    Checks the workers configuration to ensure that solo workers are configured
    correctly for the relevant queues. Sets the boolean attribute
    `is_solo_worker` on the celery app
    """
    if any(q in instance.app.amqp.queues for q in settings.CELERY_SOLO_QUEUES):
        if instance.concurrency != 1:
            raise ImproperlyConfigured("Worker concurrency must be 1")
        elif instance.autoscale is not None:
            raise ImproperlyConfigured("Worker autoscaling must be disabled")
        elif not instance.task_events:
            raise ImproperlyConfigured("Worker must send task events")
        elif instance.prefetch_multiplier != 1:
            raise ImproperlyConfigured("Worker prefetch multiplier must be 1")
        else:
            celery_app.is_solo_worker = True
            logger.info("Worker solo setup OK")
    else:
        celery_app.is_solo_worker = False
        logger.info("Worker setup OK")


@celeryd_after_setup.connect()
def set_memory_limits(*_, **__) -> None:
    if platform.system() == "Linux":
        with open("/proc/meminfo") as meminfo:
            for line in meminfo:
                if line.startswith("MemTotal:"):
                    total_memory_bytes = int(line.split()[1]) * 1024

        limit = int(
            total_memory_bytes
            * settings.CELERY_WORKER_MAX_MEMORY_PERCENTAGE
            / 100
        )

        if limit > total_memory_bytes or limit < 512 * settings.MEGABYTE:
            raise ImproperlyConfigured("Invalid memory limit")

        logger.info(f"Setting memory limit to {limit / settings.GIGABYTE} GB")
        resource.setrlimit(resource.RLIMIT_DATA, (limit, limit))
    else:
        logger.warning("Memory limits are only supported on Linux")


def get_scale_in_protection_url():
    return f"{os.environ['ECS_AGENT_URI']}/task-protection/v1/state"


@task_prerun.connect()
def set_ecs_scale_in_protection(*_, task, **__):
    if (
        celery_app.is_solo_worker
        and settings.ECS_ENABLE_CELERY_SCALE_IN_PROTECTION
    ):
        expire_seconds = task.time_limit or settings.CELERY_TASK_TIME_LIMIT
        expire_minutes = max(ceil(expire_seconds / 60), 1)

        logger.info(
            f"Setting ECS scale-in protection for {expire_minutes} minutes"
        )

        response = requests.put(
            url=get_scale_in_protection_url(),
            json={
                "ProtectionEnabled": True,
                "ExpiresInMinutes": expire_minutes,
            },
        )
        response.raise_for_status()


@task_postrun.connect()
def remove_ecs_scale_in_protection(*_, **__):
    if (
        celery_app.is_solo_worker
        and settings.ECS_ENABLE_CELERY_SCALE_IN_PROTECTION
    ):
        logger.info("Removing ECS scale-in protection")

        response = requests.put(
            url=get_scale_in_protection_url(),
            json={"ProtectionEnabled": False},
        )
        response.raise_for_status()
