from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mass_mail
from django.core.paginator import Paginator

from config import settings
from grandchallenge.algorithms.models import Algorithm
from grandchallenge.challenges.models import Challenge
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_bulk_email(action, subject, body):
    if action == SendActionChoices.MAILING_LIST:
        receivers = [
            user
            for user in get_user_model().objects.filter(
                user_profile__receive_newsletter=True
            )
        ]
    elif action == SendActionChoices.STAFF:
        receivers = [
            user for user in get_user_model().objects.filter(is_staff=True)
        ]
    elif action == SendActionChoices.CHALLENGE_ADMINS:
        receivers = [
            user
            for challenge in Challenge.objects.all()
            for user in challenge.admins_group.user_set.all()
        ]
    elif action == SendActionChoices.READER_STUDY_EDITORS:
        receivers = [
            user
            for rs in ReaderStudy.objects.all()
            for user in rs.editors_group.user_set.all()
        ]
    elif action == SendActionChoices.ALGORITHM_EDITORS:
        receivers = [
            user
            for algorithm in Algorithm.objects.all()
            for user in algorithm.editors_group.user_set.all()
        ]

    paginator = Paginator(list(set(receivers)), 1000)
    site = Site.objects.get_current()
    messages = []
    for page_nr in paginator.page_range:
        for recipient in paginator.page(page_nr).object_list:
            messages.append(
                (
                    f"[{site.domain.lower()}] {subject}",
                    f"Dear {recipient.username},"
                    f"\r\n\r\n{body}\r\n\r\n"
                    f"Kind regards, \r\nGrand Challenge team \r\n\r\n"
                    f"To unsubscribe from this mailing list, "
                    f"uncheck 'Receive newsletter' in your profile settings:"
                    f" {reverse('profile-update', kwargs={'username': recipient.username})}",
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient.email],
                )
            )
        send_mass_mail(messages)
