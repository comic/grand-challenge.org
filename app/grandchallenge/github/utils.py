from django.db import models
from django.utils.translation import gettext_lazy as _


class CloneStatusChoices(models.TextChoices):
    """Notification type choices."""

    PENDING = "PENDING", _("Pending")
    STARTED = "STARTED", _("Started")
    SUCCESS = "SUCCESS", _("Success")
    FAILURE = "FAILURE", _("Failure")
