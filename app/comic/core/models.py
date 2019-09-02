import uuid

from django.db import models


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified times
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID (primary key)"
    )
    created = models.DateTimeField(
        auto_now_add=True,
        help_text="Moment of creation"
    )
    modified = models.DateTimeField(
        auto_now=True,
        help_text="Moment of last modification"
    )

    class Meta:
        abstract = True
