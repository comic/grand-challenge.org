import time
from datetime import timedelta

import boto3
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from botocore.exceptions import BotoCoreError, ClientError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.timezone import now
from redis.exceptions import LockError

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.emails.models import Email, RawEmail
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.profiles.models import EmailSubscriptionTypes

logger = get_task_logger(__name__)


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


@acks_late_micro_short_task(
    retry_on=(SoftTimeLimitExceeded, TimeLimitExceeded),
    singleton=True,
)
def send_bulk_email(*, action, email_pk):
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

    # Transaction and locking unnecessary here as a cache lock is being used
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


@acks_late_micro_short_task(
    ignore_result=True,
    singleton=True,
    # No need to retry here as the periodic task call this again
    ignore_errors=(LockError, SoftTimeLimitExceeded, TimeLimitExceeded),
)
def send_raw_emails():
    if settings.DEBUG:
        client = None
        min_send_duration = timedelta(seconds=1)
    else:
        client = boto3.client("ses", region_name=settings.AWS_SES_REGION_NAME)
        min_send_duration = timedelta(
            seconds=1 / int(client.get_send_quota()["MaxSendRate"])
        )

    # Transaction and locking unnecessary here as a cache lock is being used
    for raw_email in RawEmail.objects.filter(
        sent_at__isnull=True, errored=False
    ).iterator():
        start = now()

        try:
            if settings.DEBUG:
                response = {"MessageId": "debug"}
            else:
                response = client.send_raw_email(
                    RawMessage={"Data": raw_email.message}
                )
        except (ClientError, BotoCoreError) as error:
            raw_email.errored = True
            raw_email.save()
            logger.error(f"Error sending raw email {raw_email.pk}: {error}")
            continue
        else:
            raw_email.sent_at = now()
            raw_email.save()
            logger.info(
                f"Sent raw email {raw_email.pk}: {response['MessageId']}"
            )

        elapsed = now() - start

        if elapsed < min_send_duration:
            time.sleep((min_send_duration - elapsed).total_seconds())


@acks_late_micro_short_task
@transaction.atomic
def cleanup_sent_raw_emails():
    RawEmail.objects.filter(
        sent_at__isnull=False,
        errored=False,
        created__lt=now() - timedelta(days=7),
    ).only("pk").delete()
