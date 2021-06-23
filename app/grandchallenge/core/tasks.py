from time import sleep

from celery import shared_task
from django.conf import settings
from django.contrib.sitemaps import ping_google as _ping_google
from django.contrib.sites.models import Site
from django.core.management import call_command

from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)


@shared_task
def clear_sessions():
    """Clear the expired sessions stored in django_session."""
    call_command("clearsessions")


@shared_task
def ping_google():
    _ping_google()


@shared_task(
    bind=True, **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"]
)
def debug_task_queue_worker(self, duration=120, check_connectivity=True):
    """Debug task for checking workers on a queue"""
    print(f"{self.acks_late=}")
    print(f"{self.reject_on_worker_lost=}")

    print(f"Sleeping {duration=}")
    sleep(duration)
    print("Awake")

    if check_connectivity:
        print("Checking db connectivity")
        site = Site.objects.get_current()
        print(f"{site=}")

        print("Checking private S3 storage connectivity")
        private_storage_object_exists = private_s3_storage.exists("test")
        print(f"{private_storage_object_exists=}")

        print("Checking protected S3 storage connectivity")
        protected_storage_object_exists = protected_s3_storage.exists("test")
        print(f"{protected_storage_object_exists=}")
