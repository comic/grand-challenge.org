from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mass_mail
from django.core.paginator import Paginator
from django.utils.timezone import now

from grandchallenge.emails.models import Email
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.subdomains.utils import reverse


def get_receivers(action):
    if action == SendActionChoices.MAILING_LIST:
        receivers = (
            get_user_model()
            .objects.filter(user_profile__receive_newsletter=True)
            .order_by("pk")
        )
    elif action == SendActionChoices.STAFF:
        receivers = (
            get_user_model().objects.filter(is_staff=True).order_by("pk")
        )
    elif action == SendActionChoices.CHALLENGE_ADMINS:
        receivers = (
            get_user_model()
            .objects.filter(
                groups__admins_of_challenge__isnull=False,
                user_profile__receive_newsletter=True,
            )
            .distinct()
            .order_by("pk")
        )
    elif action == SendActionChoices.READER_STUDY_EDITORS:
        receivers = (
            get_user_model()
            .objects.filter(
                groups__editors_of_readerstudy__isnull=False,
                user_profile__receive_newsletter=True,
            )
            .distinct()
            .order_by("pk")
        )
    elif action == SendActionChoices.ALGORITHM_EDITORS:
        receivers = (
            get_user_model()
            .objects.filter(
                groups__editors_of_algorithm__isnull=False,
                user_profile__receive_newsletter=True,
            )
            .distinct()
            .order_by("pk")
        )

    return receivers


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_bulk_email(action, email_pk):
    try:
        email = Email.objects.filter(sent=False).get(pk=email_pk)
    except ObjectDoesNotExist:
        return
    subject = email.subject
    body = email.body
    receivers = get_receivers(action=action)
    paginator = Paginator(receivers, 100)
    site = Site.objects.get_current()
    if email.status_report:
        start_page = email.status_report["last_processed_batch"]
    else:
        start_page = 0
    for page_nr in paginator.page_range[start_page:]:
        messages = []
        for recipient in paginator.page(page_nr).object_list:
            user = get_user_model().objects.get(pk=recipient.pk)
            messages.append(
                (
                    f"[{site.domain.lower()}] {subject}",
                    f"Dear {user.username},"
                    f"\n\n{body}\n\n"
                    f"Kind regards, \nGrand Challenge team \n\n"
                    f"To unsubscribe from this mailing list, "
                    f"uncheck 'Receive newsletter' in your profile settings:"
                    f" {reverse('profile-update', kwargs={'username': user.username})}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
            )
        send_mass_mail(messages)
        email.status_report = {"last_processed_batch": page_nr}
        email.save()

    email.sent = True
    email.sent_at = now()
    email.status_report = None
    email.save()
