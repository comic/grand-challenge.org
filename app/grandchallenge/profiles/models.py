import hashlib
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import Signer
from django.db import models
from django.db.models import TextChoices
from django.db.models.signals import post_save
from django.template.defaultfilters import pluralize
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from guardian.shortcuts import assign_perm
from guardian.utils import get_anonymous_user
from stdimage import JPEGField

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import get_mugshot_path
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.subdomains.utils import reverse

UNSUBSCRIBE_SALT = "email-subscription-preferences"


class EmailSubscriptionTypes(TextChoices):
    NEWSLETTER = "NEWSLETTER"
    NOTIFICATION = "NOTIFICATION"
    SYSTEM = "SYSTEM"


class NotificationEmailOptions(TextChoices):
    DAILY_SUMMARY = "DAILY_SUMMARY", _("Send me an email with a daily summary")
    DISABLED = "DISABLED", _("Do not send me notification emails")
    INSTANT = "INSTANT", _("Send me an email immediately")


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
    notification_email_choice = models.CharField(
        max_length=13,
        choices=NotificationEmailOptions,
        default=NotificationEmailOptions.DAILY_SUMMARY,
        help_text=(
            "Whether to receive emails about unread notifications and direct messages, and how often (immediately vs. once a day if necessary)."
        ),
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
        """Returns a small profile image"""
        try:
            return self.mugshot.x02.url
        except AttributeError:
            return self.get_gravatar_url(size=64)

    def get_gravatar_url(self, *, size=512):
        email_encoded = self.user.email.lower().encode("utf-8")
        email_hash = hashlib.sha256(email_encoded).hexdigest()
        params = urlencode({"d": "identicon", "s": str(size)})
        return f"https://www.gravatar.com/avatar/{email_hash}?{params}"

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
        return Signer(salt=UNSUBSCRIBE_SALT).sign_object(
            {"username": self.user.username}
        )

    def get_unsubscribe_link(self, *, subscription_type):
        if not self.user.is_active:
            raise ValueError("Inactive users cannot be emailed")
        elif subscription_type == EmailSubscriptionTypes.NEWSLETTER:
            if self.receive_newsletter:
                return reverse(
                    "newsletter-unsubscribe",
                    kwargs={"token": self.unsubscribe_token},
                )
            else:
                raise ValueError("User has opted out of newsletter emails")
        elif subscription_type == EmailSubscriptionTypes.NOTIFICATION:
            if (
                self.notification_email_choice
                == NotificationEmailOptions.DISABLED
            ):
                raise ValueError("User has opted out of notification emails")
            else:
                return reverse(
                    "notification-unsubscribe",
                    kwargs={"token": self.unsubscribe_token},
                )
        elif subscription_type == EmailSubscriptionTypes.SYSTEM:
            return None
        else:
            raise NotImplementedError(
                f"Unknown subscription type: {subscription_type}"
            )

    def dispatch_unread_notifications_email(
        self, *, site, unread_notification_count
    ):
        self.notification_email_last_sent_at = now()
        self.save(update_fields=["notification_email_last_sent_at"])

        subject = format_html(
            ("You have {unread_notification_count} new notification{suffix}"),
            unread_notification_count=unread_notification_count,
            suffix=pluralize(unread_notification_count),
        )

        msg = format_html(
            (
                "You have {unread_notification_count} new notification{suffix}.\n\n"
                "Read and manage your notifications [here]({url})."
            ),
            unread_notification_count=unread_notification_count,
            suffix=pluralize(unread_notification_count),
            url=reverse("notifications:list"),
        )

        send_standard_email_batch(
            site=site,
            subject=subject,
            markdown_message=msg,
            recipients=[self.user],
            subscription_type=EmailSubscriptionTypes.NOTIFICATION,
        )

    def dispatch_unread_direct_messages_email(
        self, *, site, new_unread_message_count, new_senders
    ):
        self.unread_messages_email_last_sent_at = now()
        self.save(update_fields=["unread_messages_email_last_sent_at"])

        new_sender_first_names = [s.first_name for s in new_senders]

        subject = format_html(
            (
                "You have {new_unread_message_count} new message{suffix} "
                "from {new_senders}"
            ),
            new_unread_message_count=new_unread_message_count,
            suffix=pluralize(new_unread_message_count),
            new_senders=oxford_comma(new_sender_first_names),
        )

        msg = format_html(
            (
                "You have {new_unread_message_count} new message{suffix} from {new_senders}.\n\n"
                "To read and manage your messages, click [here]({url})."
            ),
            new_unread_message_count=new_unread_message_count,
            suffix=pluralize(new_unread_message_count),
            new_senders=oxford_comma(new_sender_first_names),
            url=reverse("direct-messages:conversation-list"),
        )

        send_standard_email_batch(
            site=site,
            subject=subject,
            markdown_message=msg,
            recipients=[self.user],
            subscription_type=EmailSubscriptionTypes.NOTIFICATION,
        )


class UserProfileUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"change_userprofile"})

    content_object = models.ForeignKey(UserProfile, on_delete=models.CASCADE)


class UserProfileGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(UserProfile, on_delete=models.CASCADE)


@disable_for_loaddata
def create_user_profile(instance, created, *_, **__):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)


class BannedEmailAddress(UUIDModel):
    email = models.EmailField(
        unique=True,
        blank=False,
        help_text="Email addresses that are banned from registering.",
    )
    reason = models.TextField(
        blank=False, help_text="The reason why this email address is banned."
    )

    def __str__(self):
        return self.email

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        self.email = get_user_model().objects.normalize_email(self.email)
