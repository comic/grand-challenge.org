import boto3
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.db.models import Count
from django.utils import timezone

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.evaluation.models import Evaluation, Method
from grandchallenge.workstations.models import Session


@acks_late_micro_short_task
def clear_sessions():
    """Clear the expired sessions stored in django_session."""
    call_command("clearsessions")


@acks_late_micro_short_task(ignore_result=True)
def put_cloudwatch_metrics():
    client = boto3.client(
        "cloudwatch", region_name=settings.AWS_CLOUDWATCH_REGION_NAME
    )
    metrics = _get_metrics()

    for metric in metrics:
        # Limit of 20 metrics per call, each model can have up to 11 status
        # elements, so send individually
        if metric["MetricData"]:
            client.put_metric_data(
                Namespace=metric["Namespace"], MetricData=metric["MetricData"]
            )


def _get_metrics():
    site = Site.objects.get_current()
    metric_data = []

    # Create CloudWatch metrics for a choice field in a model
    models = [Job, Evaluation, Session, RawImageUploadSession]
    field = "status"

    for model in models:
        choice_to_display = dict(getattr(model, field).field.choices)

        def choice_to_name(choice):
            return f"{model.__name__}s{choice_to_display[choice]}".translate(
                {ord(c): None for c in " -."}
            )

        qs = model.objects.values(field).annotate(Count(field)).order_by(field)
        counts = {q[field]: q[f"{field}__count"] for q in qs}

        metric_data.append(
            {
                "Namespace": f"{site.domain}/{model._meta.app_label}",
                "MetricData": [
                    {
                        "MetricName": choice_to_name(c),
                        "Value": counts.get(c, 0),
                        "Unit": "Count",
                    }
                    for c in choice_to_display
                ],
            }
        )

    now = timezone.now()
    component_metric_data = []

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
        try:
            total_seconds = (
                now - queryset.order_by("created").first().created
            ).total_seconds()
        except AttributeError:
            total_seconds = 0

        component_metric_data.append(
            {
                "MetricName": f"OldestActive{queryset.model.__name__}",
                "Value": total_seconds,
                "Unit": "Seconds",
            }
        )

    metric_data.append(
        {
            "Namespace": f"{site.domain}/AsyncTasks",
            "MetricData": component_metric_data,
        }
    )

    return metric_data
