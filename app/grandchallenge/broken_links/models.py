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


class IgnoredPattern(UUIDModel):
    pattern = models.CharField(
        max_length=512,
        unique=True,
        help_text="Regex pattern for paths to ignore.",
    )

    def __str__(self):
        return self.pattern

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        BrokenLink.objects.filter(path__regex=self.pattern).delete()
