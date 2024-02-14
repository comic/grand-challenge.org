from hashlib import md5
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import Signer
from django.db import models
from django.db.models import TextChoices
from django.db.models.signals import post_save
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm
from guardian.utils import get_anonymous_user
from stdimage import JPEGField

from grandchallenge.core.storage import get_mugshot_path
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.subdomains.utils import reverse


class SubscriptionTypes(TextChoices):
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notification"


UNSUBSCRIBE_SALT = "subscription-preferences"


class UserProfile(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        unique=True,
        verbose_name=_("user"),
        related_name="user_profile",
        on_delete=models.CASCADE,
    )

    mugshot = JPEGField(
        _("mugshot"),
        blank=True,
        upload_to=get_mugshot_path,
        help_text=_("A personal image displayed in your profile."),
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
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
        help_text="Whether to receive notification emails",
    )
    notification_email_last_sent_at = models.DateTimeField(
        default=None, null=True, editable=False
    )
    unread_messages_email_last_sent_at = models.DateTimeField(
        default=None, null=True, editable=False
    )
    receive_newsletter = models.BooleanField(
        null=True,
        blank=True,
        help_text="Would you like to be put on our mailing list and receive newsletters about Grand Challenge updates?",
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        if self.user != get_anonymous_user():
            assign_perm("change_userprofile", self.user, self)

    def get_absolute_url(self):
        return reverse(
            "profile-detail", kwargs={"username": self.user.username}
        )

    def get_mugshot_url(self):
        if self.mugshot:
            return self.mugshot.x02.url
        else:
            gravatar_url = (
                "https://www.gravatar.com/avatar/"
                + md5(self.user.email.lower().encode("utf-8")).hexdigest()
                + "?"
            )
            gravatar_url += urlencode({"d": "identicon", "s": "64"})
            return gravatar_url

    @property
    def has_unread_notifications(self):
        return self.unread_notifications.exists()

    @property
    def unread_notifications(self):
        return self.user.notification_set.filter(read=False)

    @property
    def is_incomplete(self):
        return (
            not self.user.first_name
            or not self.user.last_name
            or not self.institution
            or not self.department
            or not self.country
        )

    @property
    def user_info(self):
        return format_html(
            "<span>{}<br/>{}<br/>{}<br/>{}</span>",
            self.user.get_full_name(),
            self.institution,
            self.department,
            self.country.name,
        )

    @cached_property
    def unsubscribe_token(self):
        return Signer(salt=UNSUBSCRIBE_SALT).sign(self.user.username)

    def unsubscribe(self, subscription_type):
        if (
            subscription_type == SubscriptionTypes.NOTIFICATION
            and self.receive_notification_emails
        ):
            self.receive_notification_emails = False
        elif (
            subscription_type == SubscriptionTypes.NEWSLETTER
            and self.receive_newsletter
        ):
            self.receive_newsletter = False
        else:
            raise NotImplementedError(
                f"Unsubscribing for {subscription_type} not implemented."
            )
        self.save()


class UserProfileUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(UserProfile, on_delete=models.CASCADE)


class UserProfileGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(UserProfile, on_delete=models.CASCADE)


@disable_for_loaddata
def create_user_profile(instance, created, *_, **__):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)
