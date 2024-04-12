import logging

import boto3
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.emails.models import Email, RawEmail
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.profiles.models import EmailSubscriptionTypes

logger = logging.getLogger(__name__)


def get_receivers(action):
    if action == SendActionChoices.MAILING_LIST:
        receivers = (
            get_user_model()
            .objects.filter(
                user_profile__receive_newsletter=True, is_active=True
            )
            .order_by("pk")
        )
    elif action == SendActionChoices.STAFF:
        receivers = (
            get_user_model()
            .objects.filter(is_staff=True, is_active=True)
            .order_by("pk")
        )
    elif action == SendActionChoices.CHALLENGE_ADMINS:
        receivers = (
            get_user_model()
            .objects.filter(
                groups__admins_of_challenge__isnull=False,
                user_profile__receive_newsletter=True,
                is_active=True,
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
                is_active=True,
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
                is_active=True,
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
    receivers = get_receivers(action=action)
    paginator = Paginator(receivers, 100)
    site = Site.objects.get_current()
    if email.status_report:
        start_page = email.status_report["last_processed_batch"]
    else:
        start_page = 0
    for page_nr in paginator.page_range[start_page:]:
        send_standard_email_batch(
            site=site,
            recipients=paginator.page(page_nr).object_list,
            subject=email.subject,
            markdown_message=email.body,
            subscription_type=(
                EmailSubscriptionTypes.SYSTEM
                if action == SendActionChoices.STAFF
                else EmailSubscriptionTypes.NEWSLETTER
            ),
        )
        email.status_report = {"last_processed_batch": page_nr}
        email.save()

    email.sent = True
    email.sent_at = now()
    email.status_report = None
    email.save()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_raw_email(*, raw_email_pk):
    queryset = RawEmail.objects.filter(
        pk=raw_email_pk, sent_at__isnull=True
    ).select_for_update()

    with transaction.atomic():
        try:
            # Acquire lock
            raw_email = queryset.get()
        except ObjectDoesNotExist:
            return

        client = boto3.client("ses", region_name=settings.AWS_SES_REGION_NAME)
        client.send_raw_email(
            RawMessage={
                "Data": raw_email.message,
            },
        )

        raw_email.sent_at = now()
        raw_email.save()
