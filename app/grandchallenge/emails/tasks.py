import logging
import time
from datetime import timedelta

import boto3
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.utils.timezone import now
from redis.exceptions import LockError

from grandchallenge.components.tasks import _retry
from grandchallenge.core.cache import _cache_key_from_method
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
def send_bulk_email(*, action, email_pk, retries=0):
    try:
        with cache.lock(
            _cache_key_from_method(send_bulk_email),
            timeout=settings.CELERY_TASK_TIME_LIMIT,
            blocking_timeout=1,
        ):
            _send_bulk_email(action=action, email_pk=email_pk)
    except (LockError, SoftTimeLimitExceeded, TimeLimitExceeded) as error:
        logger.info(f"send_bulk_email failed with: {error}")
        _retry(
            task=send_bulk_email,
            signature_kwargs={
                "kwargs": {
                    "action": action,
                    "email_pk": email_pk,
                },
                "immutable": True,
            },
            retries=retries,
        )


def _send_bulk_email(*, action, email_pk):
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


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"],
    ignore_result=True,
)
def send_raw_emails():
    try:
        with cache.lock(
            _cache_key_from_method(send_raw_emails),
            timeout=settings.CELERY_TASK_TIME_LIMIT,
            blocking_timeout=1,
        ):
            _send_raw_emails()
    except (LockError, SoftTimeLimitExceeded, TimeLimitExceeded) as error:
        # No need to retry here as the periodic task call this again
        logger.info(f"send_raw_emails failed with: {error}")


def _send_raw_emails():
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
        except Exception as error:
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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def cleanup_sent_raw_emails():
    RawEmail.objects.filter(
        sent_at__isnull=False,
        errored=False,
        created__lt=now() - timedelta(days=7),
    ).delete()
