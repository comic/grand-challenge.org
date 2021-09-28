import boto3
from celery import shared_task
from django.contrib.sitemaps import ping_google as _ping_google
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.db.models import Count

from grandchallenge.algorithms.models import Job
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.workstations.models import Session


@shared_task
def clear_sessions():
    """Clear the expired sessions stored in django_session."""
    call_command("clearsessions")


@shared_task
def ping_google():
    _ping_google()


@shared_task
def put_cloudwatch_metrics():
    client = boto3.client("cloudwatch")
    metrics = _get_metrics()

    for metric in metrics:
        # Limit of 20 metrics per call, each model can have up to 11 status
        # elements, so send individually
        if metric["MetricData"]:
            client.put_metric_data(
                Namespace=metric["Namespace"], MetricData=metric["MetricData"],
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

    return metric_data
