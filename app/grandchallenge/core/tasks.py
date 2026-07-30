import boto3
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import Count
from django.utils import timezone
from lambda_tasks.decorators import lambda_task
from pictures.tasks import _process_picture

from config.lambda_tasks import LambdaTaskQueueChoices
from grandchallenge.algorithms.models import AlgorithmImage, Endpoint, Job
from grandchallenge.cases.models import (
    PostProcessImageTask,
    RawImageUploadSession,
)
from grandchallenge.evaluation.models import Evaluation, Method
from grandchallenge.workstations.models import Session

CLOUDWATCH_METRICS_LIMIT = 1000


@lambda_task(
    singleton=True,
    # No need to retry here as the periodic task calls this again
    retry_singleton=False,
)
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
        Endpoint,
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
        Endpoint.objects.filter(status=Endpoint.StatusChoices.QUEUED),
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

    metric_data.append(
        {
            "MetricName": "LeftoverEndpointsOnSagemaker",
            "Dimensions": [{"Name": "Model", "Value": Endpoint.__name__}],
            "Value": _count_leftover_endpoints_on_sagemaker(),
            "Unit": "Count",
        }
    )

    return metric_data


def _count_leftover_endpoints_on_sagemaker():
    sagemaker_client = boto3.client(
        "sagemaker",
        region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
    )

    active_endpoint_names = {
        endpoint.endpoint_name for endpoint in Endpoint.objects.active()
    }

    count = 0
    paginator = sagemaker_client.get_paginator("list_endpoints")

    for page in paginator.paginate():
        for endpoint in page["Endpoints"]:
            if endpoint["EndpointName"] not in active_endpoint_names:
                count += 1

    return count


def schedule_process_picture(
    storage: list | tuple,
    file_name: str,
    new: list | tuple | None = None,
    old: list | tuple | None = None,
):
    process_picture.execute_on_commit(
        storage=storage, file_name=file_name, new=new, old=old
    )


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def process_picture(
    *,
    storage: list | tuple,
    file_name: str,
    new: list | tuple | None = None,
    old: list | tuple | None = None,
):
    _process_picture(storage=storage, file_name=file_name, new=new, old=old)
