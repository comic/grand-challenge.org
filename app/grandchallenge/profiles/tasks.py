from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session


@shared_task
def deactivate_user(*, user_pk):
    user = get_user_model().objects.get(pk=user_pk)

    user.is_active = False
    user.save()

    for s in Session.objects.all():
        if str(s.get_decoded().get("_auth_user_id")) == str(user.id):
            s.delete()
