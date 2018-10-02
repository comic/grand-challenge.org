from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField
from userena.models import UserenaBaseProfile

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.utils import disable_for_loaddata


class UserProfile(UserenaBaseProfile):
    user = models.OneToOneField(
        User,
        unique=True,
        verbose_name=_("user"),
        related_name="user_profile",
        on_delete=models.CASCADE,
    )

    institution = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    country = CountryField()
    website = models.CharField(max_length=150, blank=True)

    def get_challenges_as_participant(self):
        return Challenge.objects.filter(
            participants_group__in=self.user.groups.all()
        ).filter(hidden=False)


@disable_for_loaddata
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)
