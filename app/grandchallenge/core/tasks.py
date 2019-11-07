from celery import shared_task
from django.core.management import call_command


@shared_task
def clear_sessions():
    """Clear the expired sessions stored in django_session."""
    call_command("clearsessions")
