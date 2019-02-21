import logging

from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel

logger = logging.getLogger(__name__)


def get_container_file_name(obj, filename):
    return 'evaluators/'+str(obj.id)


# An evaluator takes the output of an algorithm and converts it into a JSON object (metrics)
class Evaluator(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="evaluators",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20, null=False, blank=False)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this Evaluator in markdown.",
    )
    container = models.FileField(blank=True, upload_to=get_container_file_name)
