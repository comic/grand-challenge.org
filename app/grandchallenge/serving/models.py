from django.conf import settings
from django.db import models

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
    submission_supplementary = models.ForeignKey(
        Submission,
        null=True,
        on_delete=models.CASCADE,
        editable=False,
        related_name="supplementary_file_downloads",
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
    *,
    user,
    civ_pk=None,
    interface=None,
):
    extra_filter_kwargs = {}
    if interface:
        extra_filter_kwargs["interface"] = interface
    if civ_pk:
        extra_filter_kwargs["pk"] = civ_pk

    civs = ComponentInterfaceValue.objects.filter(**extra_filter_kwargs)

    if not civs:
        return civs

    job_query = filter_by_permission(
        queryset=Job.objects.all(),
        user=user,
        codename="view_job",
        accept_user_perms=False,
    )

    job_inputs = (
        job_query.filter(inputs__in=civs)
        .distinct()
        .values_list("inputs__pk", flat=True)
    )
    job_outputs = (
        job_query.filter(outputs__in=civs)
        .distinct()
        .values_list("outputs__pk", flat=True)
    )

    display_sets = (
        filter_by_permission(
            queryset=DisplaySet.objects.all(),
            user=user,
            codename="view_displayset",
            accept_user_perms=False,
        )
        .filter(values__in=civs)
        .distinct()
        .values_list("values__pk", flat=True)
    )

    archive_items = (
        filter_by_permission(
            queryset=ArchiveItem.objects.all(),
            user=user,
            codename="view_archiveitem",
            accept_user_perms=False,
        )
        .filter(values__in=civs)
        .distinct()
        .values_list("values__pk", flat=True)
    )

    return civs.filter(
        pk__in=[
            *job_inputs,
            *job_outputs,
            *display_sets,
            *archive_items,
        ]
    )
