from datetime import timedelta

import boto3
from billiard.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.timezone import now
from django_celery_results.models import TaskResult
from redis.exceptions import LockError

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.cases.models import (
    PostProcessImageTask,
    RawImageUploadSession,
)
from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.evaluation.models import Evaluation, Method
from grandchallenge.workstations.models import Session


@acks_late_micro_short_task
@transaction.atomic
def cleanup_celery_backend():
    """Cleanup the Celery backend."""
    TaskResult.objects.filter(date_created__lt=now() - timedelta(days=7)).only(
        "pk"
    ).delete()


CLOUDWATCH_METRICS_LIMIT = 1000


@acks_late_micro_short_task(
    ignore_result=True,
    singleton=True,
    # No need to retry here as the periodic task call this again
    ignore_errors=(LockError, SoftTimeLimitExceeded),
)
@transaction.atomic
def put_cloudwatch_metrics():
    if not settings.PUSH_CLOUDWATCH_METRICS:
        return

    client = boto3.client(
        "cloudwatch", region_name=settings.AWS_CLOUDWATCH_REGION_NAME
    )

    site = Site.objects.get_current()
    namespace = f"{site.domain}/model-tasks"
    metric_data = _get_metrics()

    for idx in range(0, len(metric_data), CLOUDWATCH_METRICS_LIMIT):
        client.put_metric_data(
            Namespace=namespace,
            MetricData=metric_data[idx : idx + CLOUDWATCH_METRICS_LIMIT],
        )


def _get_metrics():
    metric_data = []

    models = [
        Job,
        Evaluation,
        Session,
        RawImageUploadSession,
        PostProcessImageTask,
    ]
    field = "status"

    for model in models:
        choice_to_display = dict(getattr(model, field).field.choices)

        def choice_to_name(choice):
            return f"{model.__name__}s{choice_to_display[choice]}".translate(
                {ord(c): None for c in " -."}
            )

        qs = model.objects.values(field).annotate(Count(field)).order_by(field)
        counts = {q[field]: q[f"{field}__count"] for q in qs}

        metric_data.extend(
            [
                {
                    "MetricName": choice_to_name(c),
                    "Dimensions": [{"Name": "Model", "Value": model.__name__}],
                    "Value": counts.get(c, 0),
                    "Unit": "Count",
                }
                for c in choice_to_display
            ]
        )

    now = timezone.now()

    for queryset in (
        AlgorithmImage.objects.filter(
            import_status__in=[
                AlgorithmImage.ImportStatusChoices.QUEUED,
                AlgorithmImage.ImportStatusChoices.STARTED,
            ]
        ),
        Method.objects.filter(
            import_status__in=[
                Method.ImportStatusChoices.QUEUED,
                Method.ImportStatusChoices.STARTED,
            ]
        ),
        Evaluation.objects.active(),
        Job.objects.active(),
        RawImageUploadSession.objects.filter(
            status__in=[
                RawImageUploadSession.REQUEUED,
                RawImageUploadSession.STARTED,
            ]
        ),
        Session.objects.filter(status=Session.QUEUED),
    ):
        oldest = queryset.order_by("created").values("created").first()
        total_seconds = (
            (now - oldest["created"]).total_seconds() if oldest else 0
        )
        metric_data.append(
            {
                "MetricName": f"OldestActive{queryset.model.__name__}",
                "Value": total_seconds,
                "Unit": "Seconds",
            }
        )

    return metric_data
