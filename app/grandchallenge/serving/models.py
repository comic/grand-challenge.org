from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    AlgorithmModel,
    Job,
)
from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.evaluation.models import Submission
from grandchallenge.reader_studies.models import DisplaySet
from grandchallenge.workstations.models import Feedback


class Download(models.Model):
    """Tracks who downloaded objects."""

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, editable=False
    )

    image = models.ForeignKey(
        Image, null=True, on_delete=models.CASCADE, editable=False
    )
    submission = models.ForeignKey(
        Submission, null=True, on_delete=models.CASCADE, editable=False
    )
    component_interface_value = models.ForeignKey(
        ComponentInterfaceValue,
        null=True,
        on_delete=models.CASCADE,
        editable=False,
    )
    challenge_request = models.ForeignKey(
        ChallengeRequest, null=True, on_delete=models.CASCADE, editable=False
    )
    feedback = models.ForeignKey(
        Feedback, null=True, on_delete=models.CASCADE, editable=False
    )
    algorithm_model = models.ForeignKey(
        AlgorithmModel, null=True, on_delete=models.CASCADE, editable=False
    )
    algorithm_image = models.ForeignKey(
        AlgorithmImage, null=True, on_delete=models.CASCADE, editable=False
    )


def get_component_interface_values_for_user(
    *, user, civ_pk=None, interface=None
):
    job_query = filter_by_permission(
        queryset=Job.objects.all(),
        user=user,
        codename="view_job",
    )
    job_inputs_query = job_query.filter(inputs__pk__in=OuterRef("pk"))
    job_outputs_query = job_query.filter(outputs__pk__in=OuterRef("pk"))

    display_set_query = filter_by_permission(
        queryset=DisplaySet.objects.all(),
        user=user,
        codename="view_displayset",
    ).filter(values__pk__in=OuterRef("pk"))

    archive_item_query = filter_by_permission(
        queryset=ArchiveItem.objects.all(),
        user=user,
        codename="view_archiveitem",
    ).filter(values__pk__in=OuterRef("pk"))

    extra_filter_kwargs = {}
    if interface:
        extra_filter_kwargs["interface"] = interface
    if civ_pk:
        extra_filter_kwargs["pk"] = civ_pk

    return (
        ComponentInterfaceValue.objects.filter(**extra_filter_kwargs)
        .annotate(
            user_has_view_permission=Exists(job_inputs_query)
            | Exists(job_outputs_query)
            | Exists(display_set_query)
            | Exists(archive_item_query)
        )
        .filter(user_has_view_permission=True)
    )
