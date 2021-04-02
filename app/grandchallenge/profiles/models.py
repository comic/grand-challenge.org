from hashlib import md5
from urllib.parse import urlencode

from actstream.models import user_stream
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from easy_thumbnails.fields import ThumbnailerImageField
from guardian.shortcuts import assign_perm

from grandchallenge.core.storage import get_mugshot_path
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.subdomains.utils import reverse


class UserProfile(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        unique=True,
        verbose_name=_("user"),
        related_name="user_profile",
        on_delete=models.CASCADE,
    )

    MUGSHOT_SETTINGS = {
        "size": (
            settings.PROFILES_MUGSHOT_SIZE,
            settings.PROFILES_MUGSHOT_SIZE,
        ),
        "crop": settings.PROFILES_MUGSHOT_SIZE,
    }

    mugshot = ThumbnailerImageField(
        _("mugshot"),
        blank=True,
        upload_to=get_mugshot_path,
        resize_source=MUGSHOT_SETTINGS,
        help_text=_("A personal image displayed in your profile."),
    )

    institution = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    country = CountryField()
    website = models.CharField(max_length=150, blank=True)
    display_organizations = models.BooleanField(
        default=True,
        help_text="Display the organizations that you are a member of in your profile.",
    )

    receive_notification_emails = models.BooleanField(
        default=True,
        help_text="Whether to receive email updates about notifications",
    )
    notification_email_last_sent_at = models.DateTimeField(
        default=None, null=True, editable=False
    )
    notifications_last_read_at = models.DateTimeField(
        default=None, null=True, editable=False
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        if self.user.username not in [
            settings.RETINA_IMPORT_USER_NAME,
            settings.ANONYMOUS_USER_NAME,
        ]:
            assign_perm("change_userprofile", self.user, self)

    def get_absolute_url(self):
        return reverse(
            "profile-detail", kwargs={"username": self.user.username}
        )

    def get_mugshot_url(self):
        if self.mugshot:
            return self.mugshot.url
        else:
            gravatar_url = (
                "https://www.gravatar.com/avatar/"
                + md5(self.user.email.lower().encode("utf-8")).hexdigest()
                + "?"
            )
            gravatar_url += urlencode(
                {"d": "identicon", "s": str(settings.PROFILES_MUGSHOT_SIZE)}
            )
            return gravatar_url

    @property
    def has_unread_notifications(self):
        return self.unread_notifications.exists()

    @property
    def unread_notifications(self):
        if self.notifications_last_read_at:
            return self.notifications.exclude(
                timestamp__lt=self.notifications_last_read_at
            )
        else:
            return self.notifications

    @property
    def notifications(self):
        notifications = user_stream(obj=self.user, since_following=True)

        # Workaround for
        # https://github.com/justquick/django-activity-stream/issues/482
        notifications = notifications.exclude(
            actor_content_type=ContentType.objects.get_for_model(self.user),
            actor_object_id=self.user.pk,
        )

        return notifications


@disable_for_loaddata
def create_user_profile(instance, created, *_, **__):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)
