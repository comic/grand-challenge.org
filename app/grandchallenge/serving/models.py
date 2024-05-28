from django.conf import settings
from django.db import models

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.components.models import ComponentInterfaceValue
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
