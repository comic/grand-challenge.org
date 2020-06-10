from celery import shared_task
from django.contrib.sitemaps import ping_google as _ping_google
from django.core.management import call_command


@shared_task
def clear_sessions():
    """Clear the expired sessions stored in django_session."""
    call_command("clearsessions")


@shared_task
def ping_google():
    _ping_google()
