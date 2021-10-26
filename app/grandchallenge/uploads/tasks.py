from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.paginator import Paginator
from django.utils.timezone import now

from grandchallenge.uploads.models import UserUpload


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def delete_old_user_uploads():
    limit = now() - timedelta(days=2)
    queryset = UserUpload.objects.filter(created__lt=limit).order_by(
        "-created"
    )
    paginator = Paginator(object_list=queryset, per_page=100)

    # Reverse iteration over the queryset as we're deleting objects
    for idx in range(paginator.num_pages, 0, -1):
        page = paginator.get_page(idx)

        # Another query as delete() cannot be used with LIMIT or OFFSET
        UserUpload.objects.filter(
            pk__in=page.object_list.values_list("pk", flat=True)
        ).delete()
