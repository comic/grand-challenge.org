from django.conf import settings
from django.db import models
from django.db.models.signals import post_save

from grandchallenge.core.utils import disable_for_loaddata


class Credit(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        unique=True,
        on_delete=models.CASCADE,
        related_name="user_credit",
    )

    credits = models.PositiveIntegerField(
        default=1000,
        help_text="The credits that a user can spend per month on running algorithms.",
    )

    def __str__(self):
        return f"Credits for {self.user}"


@disable_for_loaddata
def create_user_credit(sender, instance, created, **kwargs):
    if created:
        Credit.objects.create(user=instance)


post_save.connect(create_user_credit, sender=settings.AUTH_USER_MODEL)
