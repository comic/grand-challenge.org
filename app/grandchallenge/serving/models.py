from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef

from grandchallenge.algorithms.models import AlgorithmImage, AlgorithmModel
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.widgets import ParentObjectTypeChoices
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.evaluation.models import Submission
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


def get_component_interface_values_for_user(*, user):
    job_inputs_query = get_objects_for_user(
        user=user, perms="algorithms.view_job"
    ).filter(inputs__pk__in=OuterRef("pk"))

    job_outputs_query = get_objects_for_user(
        user=user, perms="algorithms.view_job"
    ).filter(outputs__pk__in=OuterRef("pk"))

    display_set_query = get_objects_for_user(
        user=user, perms="reader_studies.view_displayset"
    ).filter(values__pk__in=OuterRef("pk"))

    archive_item_query = get_objects_for_user(
        user=user, perms="archives.view_archiveitem"
    ).filter(values__pk__in=OuterRef("pk"))

    return ComponentInterfaceValue.objects.annotate(
        user_has_view_permission=Exists(job_inputs_query)
        | Exists(job_outputs_query)
        | Exists(display_set_query)
        | Exists(archive_item_query)
    ).filter(user_has_view_permission=True)


def get_component_interface_values_for_user_for_parent_object_type(
    *, user, parent_object_type_choice
):
    match parent_object_type_choice:
        case ParentObjectTypeChoices.JOB:
            job_inputs_query = get_objects_for_user(
                user=user, perms="algorithms.view_job"
            ).filter(inputs__pk__in=OuterRef("pk"))

            job_outputs_query = get_objects_for_user(
                user=user, perms="algorithms.view_job"
            ).filter(outputs__pk__in=OuterRef("pk"))

            return ComponentInterfaceValue.objects.annotate(
                user_has_view_permission=Exists(job_inputs_query)
                | Exists(job_outputs_query)
            ).filter(user_has_view_permission=True)
        case ParentObjectTypeChoices.DISPLAY_SET:
            query = get_objects_for_user(
                user=user, perms="reader_studies.view_displayset"
            ).filter(values__pk__in=OuterRef("pk"))
        case ParentObjectTypeChoices.ARCHIVE_ITEM:
            query = get_objects_for_user(
                user=user, perms="archives.view_archiveitem"
            ).filter(values__pk__in=OuterRef("pk"))
        case _:
            raise TypeError(
                f"Unknown parent object type: {parent_object_type_choice}"
            )
    return ComponentInterfaceValue.objects.annotate(
        user_has_view_permission=Exists(query)
    ).filter(user_has_view_permission=True)
