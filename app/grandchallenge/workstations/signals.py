from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from grandchallenge.workstations.models import Session


@receiver(user_logged_out)
def stop_users_sessions(*, user, **_):
    users_sessions = Session.objects.active().filter(creator=user)

    for session in users_sessions:
        session.status = Session.EXPIRED
        session.save()
