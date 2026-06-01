from datetime import timedelta
from uuid import UUID

import boto3
from billiard.exceptions import (
    SoftTimeLimitExceeded as CelerySoftTimeLimitExceeded,
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task
from lambda_tasks.logging import task_logger
from lambda_tasks.timeouts import SoftTimeLimitExceeded
from redis.exceptions import LockError

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.emails.models import Email, RawEmail
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.profiles.models import EmailSubscriptionTypes


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


@lambda_task(singleton=True)
def send_bulk_email(
    *, action: SendActionChoices, email_pk: int, current_page_number: int = 1
):
    with check_lock_acquired():
        email = Email.objects.select_for_update(nowait=True).get(pk=email_pk)

    if email.sent:
        task_logger.error("Email has already been sent")
        return

    receivers = get_receivers(action=action)
    paginator = Paginator(receivers, 100)
    site = Site.objects.get_current()

    send_standard_email_batch(
        site=site,
        recipients=paginator.page(current_page_number).object_list,
        subject=email.subject,
        markdown_message=email.body,
        subscription_type=(
            EmailSubscriptionTypes.SYSTEM
            if action == SendActionChoices.STAFF
            else EmailSubscriptionTypes.NEWSLETTER
        ),
    )

    if current_page_number >= paginator.num_pages:
        email.sent = True
        email.sent_at = now()
        email.save()
        return
    else:
        send_bulk_email.execute_on_commit(
            action=action,
            email_pk=email_pk,
            current_page_number=current_page_number + 1,
        )
        return


def get_max_emails_per_minute():
    client = boto3.client("ses", region_name=settings.AWS_SES_REGION_NAME)
    return min(
        60 * int(client.get_send_quota()["MaxSendRate"]),
        settings.EMAILS_MAX_SENT_PER_MINUTE,
    )


@acks_late_micro_short_task(
    name=f"{__name__}.send_raw_emails",
    singleton=True,
    # No need to retry here as the periodic task call this again
    ignore_errors=(
        LockError,
        CelerySoftTimeLimitExceeded,
        SoftTimeLimitExceeded,
    ),
)
@transaction.atomic
def send_raw_emails_celery(**kwargs):
    # TODO: 4408 Remove, this is still here to handle existing tasks on SQS
    return send_raw_emails(**kwargs)


@lambda_task(singleton=True)
def send_raw_emails():
    max_emails_per_minute = get_max_emails_per_minute()

    raw_emails = RawEmail.objects.select_for_update(skip_locked=True).filter(
        status=RawEmail.RawEmailStatusChoices.INITIALIZED,
    )[:max_emails_per_minute]

    for raw_email in raw_emails:
        send_raw_email.execute_on_commit(pk=raw_email.pk)
        raw_email.status = RawEmail.RawEmailStatusChoices.QUEUED
        raw_email.save()


@lambda_task(retry_on=(LockNotAcquiredException,))
def send_raw_email(*, pk: str | UUID):
    with check_lock_acquired():
        raw_email = RawEmail.objects.select_for_update(nowait=True).get(pk=pk)

    if raw_email.status != RawEmail.RawEmailStatusChoices.QUEUED:
        task_logger.error(f"Raw Email status is {raw_email.status}")
        return

    try:
        if settings.DEBUG:
            response = {"MessageId": "debug"}
        else:
            client = boto3.client(
                "ses", region_name=settings.AWS_SES_REGION_NAME
            )
            response = client.send_raw_email(
                RawMessage={"Data": raw_email.message}
            )
    except Exception as error:
        raw_email.status = RawEmail.RawEmailStatusChoices.FAILED
        raw_email.save()
        task_logger.error(error, exc_info=True)
    else:
        raw_email.status = RawEmail.RawEmailStatusChoices.SUCCEEDED
        raw_email.save()
        return response["MessageId"]


@acks_late_micro_short_task(name=f"{__name__}.cleanup_sent_raw_emails")
@transaction.atomic
def cleanup_sent_raw_emails_celery(**kwargs):
    # TODO: 4408 Remove, this is still here to handle existing tasks on SQS
    return cleanup_sent_raw_emails(**kwargs)


@lambda_task
def cleanup_sent_raw_emails():
    RawEmail.objects.filter(
        status=RawEmail.RawEmailStatusChoices.SUCCEEDED,
        created__lt=now() - timedelta(days=7),
    ).only("pk").delete()
