from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from grandchallenge.workstations.models import Session


@receiver(user_logged_out)
def stop_users_sessions(*, signal, sender, request, user):
    users_sessions = (
        Session.objects.all()
        .filter(creator=user)
        .exclude(status__in=[Session.FAILED, Session.STOPPED])
    )

    for session in users_sessions:
        session.user_finished = True
        session.save()
