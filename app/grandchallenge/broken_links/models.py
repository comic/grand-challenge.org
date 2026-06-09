from django.db import models

from grandchallenge.core.models import UUIDModel


class BrokenLink(UUIDModel):
    domain = models.CharField(max_length=255)
    path = models.TextField()
    referer = models.TextField()
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField(null=True)
    is_internal = models.BooleanField()

    class Meta(UUIDModel.Meta):
        indexes = [
            models.Index(fields=["-created"]),
        ]
