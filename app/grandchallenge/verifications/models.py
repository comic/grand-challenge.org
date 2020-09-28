from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class Verification(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(default=timezone.now)

    user = models.OneToOneField(
        get_user_model(), unique=True, on_delete=models.CASCADE,
    )

    email = models.EmailField(blank=True)
    email_is_verified = models.BooleanField(default=False, editable=False)
    email_verified_at = models.DateTimeField(
        blank=True, null=True, editable=False
    )

    is_verified = models.BooleanField(default=False, editable=False)
    verified_at = models.DateTimeField(blank=True, null=True, editable=False)
