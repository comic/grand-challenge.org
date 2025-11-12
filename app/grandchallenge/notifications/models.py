from actstream.actions import is_following
from actstream.models import Follow, followers
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.contrib.sites.models import Site
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.profiles.models import (
    NotificationEmailOptions,
    UserProfile,
)
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from grandchallenge.subdomains.utils import reverse


class FollowUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset(
        {"delete_follow", "view_follow", "change_follow"}
    )

    content_object = models.ForeignKey(Follow, on_delete=models.CASCADE)


class FollowGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Follow, on_delete=models.CASCADE)


class NotificationTypeChoices(models.TextChoices):
    """Notification type choices."""

    GENERIC = "GENERIC", _("Generic")
    FORUM_POST = "FORUM-POST", _("Forum post")
    FORUM_POST_REPLY = "FORUM-REPLY", _("Forum post reply")
    ACCESS_REQUEST = "ACCESS-REQUEST", _("Access request")
    REQUEST_UPDATE = "REQUEST-UPDATE", _("Request update")
    NEW_ADMIN = "NEW-ADMIN", _("New admin")
    EVALUATION_STATUS = "EVALUATION-STATUS", _("Evaluation status update")
    MISSING_METHOD = "MISSING-METHOD", _("Missing method")
    JOB_STATUS = "JOB-STATUS", _("Job status update")
    IMAGE_IMPORT_STATUS = "IMAGE-IMPORT", _("Image import status update")
    DICOM_IMAGE_IMPORT_STATUS = "DICOM-IMAGE-IMPORT", _(
        "DICOM image import status update"
    )
    FILE_COPY_STATUS = "FILE-COPY", _("Validation failed while copying file")
    CIV_VALIDATION = "CIV-VALIDATION", (
        "Component Interface Value validation failed"
    )


class Notification(UUIDModel):
    Type = NotificationTypeChoices

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="Which user does this notification correspond to?",
        on_delete=models.CASCADE,
    )

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.GENERIC,
        help_text="Of what type is this notification?",
    )

    read = models.BooleanField(default=False, db_index=True)

    context_class = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Bootstrap contextual class to style notification list items.",
    )

    # action-related fields (taken from actstream.models.Action)
    actor_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        related_name="notification_actor",
        on_delete=models.CASCADE,
        db_index=True,
    )
    actor_object_id = models.CharField(
        max_length=255, db_index=True, blank=True, null=True
    )
    actor = GenericForeignKey("actor_content_type", "actor_object_id")

    message = models.CharField(
        max_length=255, db_index=True, blank=True, null=True
    )
    description = models.TextField(blank=True, null=True)

    target_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        related_name="notification_target",
        on_delete=models.CASCADE,
        db_index=True,
    )
    target_object_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    target = GenericForeignKey("target_content_type", "target_object_id")

    action_object_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        related_name="notification_action_object",
        on_delete=models.CASCADE,
        db_index=True,
    )
    action_object_object_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    action_object = GenericForeignKey(
        "action_object_content_type", "action_object_object_id"
    )

    def __str__(self):
        return f"Notification {self.pk}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self._assign_permissions()

    def _assign_permissions(self):
        assign_perm("view_notification", self.user, self)
        assign_perm("delete_notification", self.user, self)
        assign_perm("change_notification", self.user, self)

    @staticmethod
    def send(
        *,
        kind,
        actor=None,
        action_object=None,
        target=None,
        message=None,
        description=None,
        context_class=None,
    ):
        receivers = Notification.get_receivers(
            action_object=action_object, actor=actor, kind=kind, target=target
        )
        site = Site.objects.get_current()

        for receiver in receivers:
            Notification.objects.create(
                user=receiver,
                type=kind,
                message=message,
                actor=actor,
                action_object=action_object,
                target=target,
                description=description,
                context_class=context_class,
            )
            if (
                receiver.user_profile.notification_email_choice
                == NotificationEmailOptions.INSTANT
            ):
                with check_lock_acquired():
                    user_profile = UserProfile.objects.select_for_update(
                        nowait=True
                    ).get(pk=receiver.user_profile.pk)

                user_profile.dispatch_unread_notifications_email(
                    site=site, unread_notification_count=1
                )

    @staticmethod
    def get_receivers(*, kind, actor, action_object, target):  # noqa: C901
        if (
            kind == NotificationTypeChoices.FORUM_POST
            or kind == NotificationTypeChoices.FORUM_POST_REPLY
            or kind == NotificationTypeChoices.ACCESS_REQUEST
            and target._meta.model_name != "algorithm"
            or kind == NotificationTypeChoices.REQUEST_UPDATE
        ):
            if actor:
                return {
                    follower
                    for follower in followers(target)
                    if follower != actor
                }
            else:
                return followers(target)
        elif (
            kind == NotificationTypeChoices.ACCESS_REQUEST
            and target._meta.model_name == "algorithm"
        ):
            return {
                follower
                for follower in followers(target, flag="access_request")
                if follower != actor
            }
        elif kind == NotificationTypeChoices.NEW_ADMIN:
            return {action_object}
        elif kind == NotificationTypeChoices.EVALUATION_STATUS:
            receivers = {
                admin
                for admin in target.challenge.get_admins()
                if is_following(admin, target)
            }
            if actor and is_following(actor, target):
                receivers.add(actor)
            return receivers
        elif kind == NotificationTypeChoices.MISSING_METHOD:
            return {
                admin
                for admin in target.challenge.get_admins()
                if is_following(admin, target)
            }
        elif kind == NotificationTypeChoices.JOB_STATUS:
            if actor and is_following(actor, target, flag="job-active"):
                return {actor}
            else:
                return set()
        elif kind == NotificationTypeChoices.IMAGE_IMPORT_STATUS:
            return followers(action_object)
        elif kind in [
            NotificationTypeChoices.FILE_COPY_STATUS,
            NotificationTypeChoices.CIV_VALIDATION,
        ]:
            return {actor}
        else:
            raise RuntimeError(f"Unhandled notification type {kind!r}")

    def print_notification(self, user):  # noqa: C901
        if self.type == NotificationTypeChoices.FORUM_POST:
            return format_html(
                "{profile_link} {message} {action_object} in {target} {time}.",
                profile_link=user_profile_link(self.actor),
                message=self.message,
                action_object=format_html(
                    '<a href="{}">{}</a>',
                    self.action_object.get_absolute_url(),
                    self.action_object.subject,
                ),
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.get_absolute_url(),
                    self.target,
                ),
                time=naturaltime(self.created),
            )
        elif self.type == NotificationTypeChoices.FORUM_POST_REPLY:
            return format_html(
                "{profile_link} {message} {target} {time}.",
                profile_link=user_profile_link(self.actor),
                message=self.message,
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.get_absolute_url(),
                    self.target.subject,
                ),
                time=naturaltime(self.created),
            )
        elif self.type == NotificationTypeChoices.ACCESS_REQUEST:
            if self.target_content_type.model == "challenge":
                notification_addition = format_html(
                    '<span class="text-truncate font-italic text-muted align-middle '
                    'mx-2">| Accept or decline <a href="{link}"> here </a>.</span>',
                    link=reverse(
                        "participants:registration-list",
                        kwargs={
                            "challenge_short_name": self.target.short_name
                        },
                    ),
                )
            else:
                notification_addition = ""
            return format_html(
                "{profile_link} {message} {target} {time}. {addition}",
                profile_link=user_profile_link(self.actor),
                message=self.message,
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.get_absolute_url(),
                    self.target,
                ),
                time=naturaltime(self.created),
                addition=notification_addition,
            )
        elif self.type == NotificationTypeChoices.REQUEST_UPDATE:
            if self.target._meta.model_name == "registrationrequest":
                target_url = self.target.challenge.get_absolute_url()
                target_name = self.target.challenge.short_name
            else:
                target_url = self.target.base_object.get_absolute_url()
                target_name = self.target.object_name
            return format_html(
                "Your registration request for {target} {message} {time}.",
                target=format_html(
                    '<a href="{url}">{name}</a>',
                    url=target_url,
                    name=target_name,
                ),
                message=self.message,
                time=naturaltime(self.created),
            )
        elif self.type == NotificationTypeChoices.NEW_ADMIN:
            return format_html(
                "You were {message} {target} {time}.",
                message=self.message,
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.get_absolute_url(),
                    self.target,
                ),
                time=naturaltime(self.created),
            )
        elif (
            self.type == NotificationTypeChoices.EVALUATION_STATUS
            and self.actor == user
        ):
            if self.action_object.error_message:
                error_message = format_html(
                    '<span class ="text-truncate font-italic text-muted align-middle '
                    'mx-2">| {}</span>',
                    self.action_object.error_message,
                )
            else:
                error_message = ""

            return format_html(
                "Your {action_object} to {target} {message} {time}. {error}",
                action_object=format_html(
                    '<a href="{}">{}</a>',
                    self.action_object.submission.get_absolute_url(),
                    "submission",
                ),
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.challenge.get_absolute_url(),
                    self.target.challenge.short_name,
                ),
                message=self.message,
                time=naturaltime(self.created),
                error=error_message,
            )
        elif (
            self.type == NotificationTypeChoices.EVALUATION_STATUS
            and self.actor != user
            and self.message != "succeeded"
        ):
            if self.action_object.error_message:
                error_message = format_html(
                    '<span class ="text-truncate font-italic text-muted align-middle '
                    'mx-2">| {}</span>',
                    self.action_object.error_message,
                )
            else:
                error_message = ""
            return format_html(
                "The {action_object} from {user_profile} to {target} {message} {time}. {error}",
                action_object=format_html(
                    '<a href="{}">{}</a>',
                    self.action_object.submission.get_absolute_url(),
                    "submission",
                ),
                user_profile=user_profile_link(
                    self.action_object.submission.creator
                ),
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.challenge.get_absolute_url(),
                    self.target.challenge.short_name,
                ),
                message=self.message,
                time=naturaltime(self.created),
                error=error_message,
            )
        elif (
            self.type == NotificationTypeChoices.EVALUATION_STATUS
            and self.actor != user
            and self.message == "succeeded"
        ):
            return format_html(
                "There is a new {action_object} for {target} from {user_profile} {time}.",
                action_object=format_html(
                    '<a href="{}">{}</a>',
                    self.action_object.submission.get_absolute_url(),
                    "result",
                ),
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.challenge.get_absolute_url(),
                    self.target.challenge.short_name,
                ),
                user_profile=user_profile_link(self.actor),
                time=naturaltime(self.created),
            )
        elif self.type == NotificationTypeChoices.MISSING_METHOD:
            return format_html(
                "The {action_object} from {user_profile} {time} could not be evaluated because "
                "there is no valid evaluation method for {target}.",
                action_object=format_html(
                    '<a href="{}">{}</a>',
                    self.action_object.get_absolute_url(),
                    "submission",
                ),
                user_profile=user_profile_link(self.actor),
                time=naturaltime(self.created),
                target=format_html(
                    '<a href="{}">{}</a>',
                    self.target.get_absolute_url(),
                    self.target,
                ),
            )
        elif self.type == NotificationTypeChoices.JOB_STATUS:
            if self.actor and self.actor != user:
                addition = format_html(" | {}", user_profile_link(self.actor))
            else:
                addition = ""
            return format_html(
                "{message} {time}. {addition} {description}",
                message=self.message,
                time=naturaltime(self.created),
                addition=addition,
                description=format_html(
                    '<span class="text-truncate font-italic text-muted align-middle '
                    'mx-2 ">| Inspect the output and any error messages <a href="{}">'
                    "here</a>.</span>",
                    self.description,
                ),
            )
        elif self.type == NotificationTypeChoices.IMAGE_IMPORT_STATUS:
            return format_html(
                "Your {action_object} from {time} failed "
                "with the following error: {message}",
                action_object=format_html(
                    '<a href="{}">{}</a>',
                    self.action_object.get_absolute_url(),
                    "upload",
                ),
                time=naturaltime(self.created),
                message=self.description,
            )
        elif self.type == NotificationTypeChoices.DICOM_IMAGE_IMPORT_STATUS:
            return format_html(
                "Your dicom import from {time} failed "
                "with the following error: {message}",
                time=naturaltime(self.created),
                message=self.description,
            )
        elif self.type in [
            NotificationTypeChoices.FILE_COPY_STATUS,
            NotificationTypeChoices.CIV_VALIDATION,
        ]:
            return self.description


class NotificationUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset(
        {"view_notification", "change_notification", "delete_notification"}
    )

    content_object = models.ForeignKey(Notification, on_delete=models.CASCADE)


class NotificationGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Notification, on_delete=models.CASCADE)
