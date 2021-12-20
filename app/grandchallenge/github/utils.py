from django.db import models
from django.utils.translation import gettext_lazy as _


class ZipStatusChoices(models.TextChoices):
    """Notification type choices."""

    NOT_STARTED = "NOT_STARTED", _("Not started")
    STARTED = "STARTED", _("Started")
    COMPLETED = "COMPLETED", _("Completed")
    FAILED = "FAILED", _("Failed")
