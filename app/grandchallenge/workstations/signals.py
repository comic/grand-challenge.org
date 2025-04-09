from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from grandchallenge.reader_studies.models import WorkstationSessionReaderStudy
from grandchallenge.workstations.models import Session


@receiver(user_logged_out)
def stop_users_sessions(*, user, **_):
    users_sessions = (
        Session.objects.all()
        .filter(creator=user)
        .exclude(status__in=[Session.FAILED, Session.STOPPED])
    )

    for session in users_sessions:
        session.user_finished = True
        session.save()


@receiver(m2m_changed, sender=WorkstationSessionReaderStudy)
def reader_studies_changed(
    sender, instance, action, pk_set, model, reverse, **kwargs
):
    if action == "post_add":
        for pk in pk_set:
            obj = model.objects.get(pk=pk)
            if reverse:
                reader_study = obj
                session = instance
            else:
                reader_study = instance
                session = obj
            session.session_cost.reader_studies.add(reader_study)
