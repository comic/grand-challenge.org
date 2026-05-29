from datetime import timedelta

from billiard.exceptions import (
    SoftTimeLimitExceeded as CelerySoftTimeLimitExceeded,
)
from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Max,
    Min,
)
from django.utils import timezone
from django_celery_results.models import TaskResult
from lambda_tasks.decorators import lambda_task
from lambda_tasks.timeouts import SoftTimeLimitExceeded

from grandchallenge.background_tasks.models import CeleryTaskDailyStats
from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task(
    name=f"{__name__}.aggregate_celery_daily_stats",
    singleton=True,
    # No need to retry here as the periodic task call this again
    ignore_errors=(
        CelerySoftTimeLimitExceeded,
        SoftTimeLimitExceeded,
    ),
)
@transaction.atomic
def aggregate_celery_daily_stats_celery(**kwargs):
    return aggregate_celery_daily_stats(**kwargs)


@lambda_task(
    singleton=True,
    # No need to retry here as the periodic task call this again
    ignore_errors=(
        CelerySoftTimeLimitExceeded,
        SoftTimeLimitExceeded,
    ),
)
def aggregate_celery_daily_stats():
    yesterday = (timezone.now() - timedelta(days=1)).date()

    duration_expr = ExpressionWrapper(
        F("date_done") - F("date_started"), output_field=DurationField()
    )

    base_qs = TaskResult.objects.filter(date_done__date=yesterday)

    success_stats = {
        row["task_name"]: row
        for row in base_qs.filter(status="SUCCESS", date_started__isnull=False)
        .annotate(duration=duration_expr)
        .values("task_name")
        .annotate(
            count=Count("id"),
            avg_duration=Avg("duration"),
            min_duration=Min("duration"),
            max_duration=Max("duration"),
        )
    }

    failure_counts = dict(
        base_qs.filter(status="FAILURE")
        .values("task_name")
        .annotate(count=Count("id"))
        .values_list("task_name", "count")
    )

    all_task_names = success_stats.keys() | failure_counts.keys()

    for task_name in all_task_names:
        success = success_stats.get(task_name, {})
        CeleryTaskDailyStats.objects.update_or_create(
            date=yesterday,
            task_name=task_name,
            defaults={
                "success_count": success.get("count", 0),
                "failure_count": failure_counts.get(task_name, 0),
                "avg_duration": success.get("avg_duration"),
                "min_duration": success.get("min_duration"),
                "max_duration": success.get("max_duration"),
            },
        )
