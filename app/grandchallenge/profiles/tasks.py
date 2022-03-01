from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def deactivate_user(*, user_pk):
    user = get_user_model().objects.get(pk=user_pk)

    user.is_active = False
    user.save()

    queryset = Session.objects.order_by("expire_date")
    paginator = Paginator(object_list=queryset, per_page=1000)

    # Reverse iteration over the queryset as we're deleting objects
    for idx in range(paginator.num_pages, 0, -1):
        page = paginator.get_page(idx)

        for s in page.object_list:
            if str(s.get_decoded().get("_auth_user_id")) == str(user.id):
                s.delete()
