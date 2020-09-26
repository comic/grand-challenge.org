from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField
from pyswot import is_academic
from userena.models import UserenaBaseProfile

from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.subdomains.utils import reverse


class UserProfile(UserenaBaseProfile):
    user = models.OneToOneField(
        get_user_model(),
        unique=True,
        verbose_name=_("user"),
        related_name="user_profile",
        on_delete=models.CASCADE,
    )

    institution = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    country = CountryField()
    website = models.CharField(max_length=150, blank=True)

    is_verified = models.BooleanField(default=False, editable=False)

    def get_absolute_url(self):
        return reverse(
            "userena_profile_detail", kwargs={"username": self.user.username}
        )

    def save(self, *args, **kwargs):
        if not self.is_verified:
            # For now, only academic emails are verified
            self.is_verified = is_academic(self.user.email)

        super().save(*args, **kwargs)


@disable_for_loaddata
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)
