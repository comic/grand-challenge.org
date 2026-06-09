from datetime import timedelta

from django.utils import timezone
from lambda_tasks.decorators import lambda_task

from grandchallenge.broken_links.models import (
    MAX_BROKEN_LINK_AGE_DAYS,
    BrokenLink,
)


@lambda_task
def delete_old_broken_links():
    cutoff = timezone.now() - timedelta(days=MAX_BROKEN_LINK_AGE_DAYS)
    deleted_count, _ = (
        BrokenLink.objects.filter(created__lt=cutoff).only("pk").delete()
    )
    return deleted_count
