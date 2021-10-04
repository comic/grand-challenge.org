import datetime
import logging
from itertools import chain, product

from actstream.actions import follow, unfollow
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField, CICharField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import format_html
from guardian.shortcuts import assign_perm
from guardian.utils import get_anonymous_user
from machina.apps.forum.models import Forum
from machina.apps.forum_permission.models import (
    ForumPermission,
    GroupForumPermission,
    UserForumPermission,
)
from stdimage import JPEGField
from tldextract import extract

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.challenges.emails import (
    send_challenge_created_email,
    send_external_challenge_created_email,
)
from grandchallenge.core.storage import (
    get_banner_path,
    get_logo_path,
    get_social_image_path,
    public_s3_storage,
)
from grandchallenge.evaluation.tasks import assign_evaluation_permissions
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.pages.models import Page
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse
from grandchallenge.task_categories.models import TaskType

logger = logging.getLogger(__name__)


class ChallengeManager(models.Manager):
    def non_hidden(self):
        """Filter the hidden challenge"""
        return self.filter(hidden=False)


def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError("Underscores (_) are not allowed.")


def validate_short_name(value):
    if value.lower() in settings.DISALLOWED_CHALLENGE_NAMES:
        raise ValidationError("That name is not allowed.")


class ChallengeSeries(models.Model):
    name = CICharField(max_length=64, blank=False, unique=True)
    url = models.URLField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "Challenge Series"

    def __str__(self):
        return f"{self.name}"

    @property
    def badge(self):
        return format_html(
            (
                '<span class="badge badge-info above-stretched-link" '
                'title="Associated with {0}"><i class="fas fa-globe fa-fw">'
                "</i> {0}</span>"
            ),
            self.name,
        )


class ChallengeBase(models.Model):
    CHALLENGE_ACTIVE = "challenge_active"
    CHALLENGE_INACTIVE = "challenge_inactive"
    DATA_PUB = "data_pub"

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    short_name = CICharField(
        max_length=50,
        blank=False,
        help_text=(
            "short name used in url, specific css, files etc. "
            "No spaces allowed"
        ),
        validators=[
            validate_nounderscores,
            validate_slug,
            validate_short_name,
        ],
        unique=True,
    )
    description = models.CharField(
        max_length=1024,
        default="",
        blank=True,
        help_text="Short summary of this project, max 1024 characters.",
    )
    title = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "The name of the challenge that is displayed on the All Challenges"
            " page. If this is blank the short name of the challenge will be "
            "used."
        ),
    )
    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        blank=True,
        help_text="A logo for this challenge. Should be square with a resolution of 640x640 px or higher.",
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    social_image = JPEGField(
        upload_to=get_social_image_path,
        storage=public_s3_storage,
        blank=True,
        help_text="An image for this challenge which is displayed when you post the link on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
        variations=settings.STDIMAGE_SOCIAL_VARIATIONS,
    )
    hidden = models.BooleanField(
        default=True,
        help_text="Do not display this Project in any public overview",
    )
    educational = models.BooleanField(
        default=False, help_text="It is an educational challange"
    )
    workshop_date = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Date on which the workshop belonging to this project will be held"
        ),
    )
    event_name = models.CharField(
        max_length=1024,
        default="",
        blank=True,
        null=True,
        help_text="The name of the event the workshop will be held at",
    )
    event_url = models.URLField(
        blank=True,
        null=True,
        help_text="Website of the event which will host the workshop",
    )
    publications = models.ManyToManyField(
        Publication,
        blank=True,
        help_text="Which publications are associated with this challenge?",
    )
    data_license_agreement = models.TextField(
        blank=True,
        help_text="What is the data license agreement for this challenge?",
    )

    task_types = models.ManyToManyField(
        TaskType, blank=True, help_text="What type of task is this challenge?"
    )
    modalities = models.ManyToManyField(
        ImagingModality,
        blank=True,
        help_text="What imaging modalities are used in this challenge?",
    )
    structures = models.ManyToManyField(
        BodyStructure,
        blank=True,
        help_text="What structures are used in this challenge?",
    )
    series = models.ManyToManyField(
        ChallengeSeries,
        blank=True,
        help_text="Which challenge series is this associated with?",
    )
    organizations = models.ManyToManyField(
        Organization,
        blank=True,
        help_text="The organizations associated with this challenge",
        related_name="%(class)ss",
    )

    number_of_training_cases = models.IntegerField(blank=True, null=True)
    number_of_test_cases = models.IntegerField(blank=True, null=True)
    filter_classes = ArrayField(
        CICharField(max_length=32), default=list, editable=False
    )
    highlight = models.BooleanField(
        default=False,
        help_text="Should this challenge be advertised on the home page?",
    )

    objects = ChallengeManager()

    def __str__(self):
        return self.short_name

    @property
    def public(self):
        """Helper property for consistency with other objects"""
        return not self.hidden

    def get_absolute_url(self):
        raise NotImplementedError

    @property
    def is_self_hosted(self):
        return True

    @property
    def year(self):
        if self.workshop_date:
            return self.workshop_date.year
        else:
            return self.created.year

    @property
    def upcoming_workshop_date(self):
        if self.workshop_date and self.workshop_date > datetime.date.today():
            return self.workshop_date

    @property
    def registered_domain(self):
        """
        Copied from grandchallenge_tags

        Try to find out what framework this challenge is hosted on, return
        a string which can also be an id or class in HTML
        """
        return extract(self.get_absolute_url()).registered_domain

    class Meta:
        abstract = True
        ordering = ("pk",)


class Challenge(ChallengeBase):
    banner = JPEGField(
        upload_to=get_banner_path,
        storage=public_s3_storage,
        blank=True,
        help_text=(
            "Image that gets displayed at the top of each page. "
            "Recommended resolution 2200x440 px."
        ),
        variations=settings.STDIMAGE_BANNER_VARIATIONS,
    )
    disclaimer = models.CharField(
        max_length=2048,
        default="",
        blank=True,
        null=True,
        help_text=(
            "Optional text to show on each page in the project. "
            "For showing 'under construction' type messages"
        ),
    )
    require_participant_review = models.BooleanField(
        default=False,
        help_text=(
            "If ticked, new participants need to be approved by project "
            "admins before they can access restricted pages. If not ticked, "
            "new users are allowed access immediately"
        ),
    )
    use_registration_page = models.BooleanField(
        default=True,
        help_text="If true, show a registration page on the challenge site.",
    )
    registration_page_text = models.TextField(
        default="",
        blank=True,
        help_text=(
            "The text to use on the registration page, you could include "
            "a data usage agreement here. You can use HTML markup here."
        ),
    )
    use_workspaces = models.BooleanField(default=False)
    use_evaluation = models.BooleanField(
        default=True,
        help_text=(
            "If true, use the automated evaluation system. See the evaluation "
            "page created in the Challenge site."
        ),
    )
    use_teams = models.BooleanField(
        default=False,
        help_text=(
            "If true, users are able to form teams to participate in "
            "this challenge together."
        ),
    )
    admins_group = models.OneToOneField(
        Group,
        editable=False,
        on_delete=models.PROTECT,
        related_name="admins_of_challenge",
    )
    participants_group = models.OneToOneField(
        Group,
        editable=False,
        on_delete=models.PROTECT,
        related_name="participants_of_challenge",
    )
    forum = models.OneToOneField(
        Forum, editable=False, on_delete=models.PROTECT
    )
    display_forum_link = models.BooleanField(
        default=False,
        help_text="Display a link to the challenge forum in the nav bar.",
    )

    cached_num_participants = models.PositiveIntegerField(
        editable=False, default=0
    )
    cached_num_results = models.PositiveIntegerField(editable=False, default=0)
    cached_latest_result = models.DateTimeField(
        editable=False, blank=True, null=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hidden_orig = self.hidden

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()
            self.create_forum()

        super().save(*args, **kwargs)

        if adding:
            if self.creator:
                self.add_admin(user=self.creator)
            self.update_permissions()
            self.create_forum_permissions()
            self.create_default_pages()
            self.create_default_phases()
            send_challenge_created_email(self)

        if adding or self.hidden != self._hidden_orig:
            on_commit(
                lambda: assign_evaluation_permissions.apply_async(
                    kwargs={"challenge_pk": self.pk}
                )
            )
            self.update_user_forum_permissions()

    def update_permissions(self):
        assign_perm("change_challenge", self.admins_group, self)

    def create_forum_permissions(self):
        participant_group_perms = {
            "can_see_forum",
            "can_read_forum",
            "can_start_new_topics",
            "can_reply_to_topics",
            "can_delete_own_posts",
            "can_edit_own_posts",
            "can_post_without_approval",
            "can_create_polls",
            "can_vote_in_polls",
        }
        admin_group_perms = {
            "can_lock_topics",
            "can_edit_posts",
            "can_delete_posts",
            "can_approve_posts",
            "can_reply_to_locked_topics",
            "can_post_announcements",
            "can_post_stickies",
            *participant_group_perms,
        }

        permissions = ForumPermission.objects.filter(
            codename__in=admin_group_perms
        ).values_list("codename", "pk")
        permissions = {codename: pk for codename, pk in permissions}

        GroupForumPermission.objects.bulk_create(
            chain(
                (
                    GroupForumPermission(
                        permission_id=permissions[codename],
                        group=self.participants_group,
                        forum=self.forum,
                        has_perm=True,
                    )
                    for codename in participant_group_perms
                ),
                (
                    GroupForumPermission(
                        permission_id=permissions[codename],
                        group=self.admins_group,
                        forum=self.forum,
                        has_perm=True,
                    )
                    for codename in admin_group_perms
                ),
            )
        )

        UserForumPermission.objects.bulk_create(
            UserForumPermission(
                permission_id=permissions[codename],
                **{user: True},
                forum=self.forum,
                has_perm=not self.hidden,
            )
            for codename, user in product(
                ["can_see_forum", "can_read_forum"],
                ["anonymous_user", "authenticated_user"],
            )
        )

    def update_user_forum_permissions(self):
        perms = UserForumPermission.objects.filter(
            permission__codename__in=["can_see_forum", "can_read_forum"],
            forum=self.forum,
        )

        for p in perms:
            p.has_perm = not self.hidden

        UserForumPermission.objects.bulk_update(perms, ["has_perm"])

    def create_groups(self):
        # Create the groups only on first save
        admins_group = Group.objects.create(name=f"{self.short_name}_admins")
        participants_group = Group.objects.create(
            name=f"{self.short_name}_participants"
        )
        self.admins_group = admins_group
        self.participants_group = participants_group

    def create_forum(self):
        f, created = Forum.objects.get_or_create(
            name=settings.FORUMS_CHALLENGE_CATEGORY_NAME, type=Forum.FORUM_CAT,
        )

        if created:
            UserForumPermission.objects.bulk_create(
                UserForumPermission(
                    permission_id=perm_id,
                    **{user: True},
                    forum=f,
                    has_perm=True,
                )
                for perm_id, user in product(
                    ForumPermission.objects.filter(
                        codename__in=["can_see_forum", "can_read_forum"]
                    ).values_list("pk", flat=True),
                    ["anonymous_user", "authenticated_user"],
                )
            )

        self.forum = Forum.objects.create(
            name=self.title if self.title else self.short_name,
            parent=f,
            type=Forum.FORUM_POST,
        )

    def create_default_pages(self):
        Page.objects.create(
            title=self.short_name,
            html=render_to_string(
                "pages/defaults/home.html", {"challenge": self}
            ),
            challenge=self,
            permission_level=Page.ALL,
        )
        Page.objects.create(
            title="Contact",
            html=render_to_string(
                "pages/defaults/contact.html", {"challenge": self}
            ),
            challenge=self,
            permission_level=Page.REGISTERED_ONLY,
        )

    def create_default_phases(self):
        self.phase_set.create(challenge=self)

    def is_admin(self, user) -> bool:
        """Determines if this user is an admin of this challenge."""
        return (
            user.is_superuser
            or user.groups.filter(pk=self.admins_group.pk).exists()
        )

    def is_participant(self, user) -> bool:
        """Determines if this user is a participant of this challenge."""
        return (
            user.is_superuser
            or user.groups.filter(pk=self.participants_group.pk).exists()
        )

    def get_admins(self):
        """Return all admins of this challenge."""
        return self.admins_group.user_set.all()

    def get_participants(self):
        """Return all participants of this challenge."""
        return self.participants_group.user_set.all()

    def get_absolute_url(self):
        return reverse(
            "pages:home", kwargs={"challenge_short_name": self.short_name},
        )

    def add_participant(self, user):
        if user != get_anonymous_user():
            user.groups.add(self.participants_group)
            follow(
                user=user, obj=self.forum, actor_only=False, send_action=False
            )
        else:
            raise ValueError("You cannot add the anonymous user to this group")

    def remove_participant(self, user):
        user.groups.remove(self.participants_group)
        unfollow(user=user, obj=self.forum, send_action=False)

    def add_admin(self, user):
        if user != get_anonymous_user():
            user.groups.add(self.admins_group)
            follow(
                user=user, obj=self.forum, actor_only=False, send_action=False
            )
        else:
            raise ValueError("You cannot add the anonymous user to this group")

    def remove_admin(self, user):
        user.groups.remove(self.admins_group)
        unfollow(user=user, obj=self.forum, send_action=False)

    class Meta(ChallengeBase.Meta):
        verbose_name = "challenge"
        verbose_name_plural = "challenges"


@receiver(post_delete, sender=Challenge)
def delete_challenge_groups_hook(*_, instance: Challenge, using, **__):
    """
    Deletes the related groups.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    try:
        instance.admins_group.delete(using=using)
    except ObjectDoesNotExist:
        pass

    try:
        instance.participants_group.delete(using=using)
    except ObjectDoesNotExist:
        pass


class ExternalChallenge(ChallengeBase):
    homepage = models.URLField(
        blank=False, help_text=("What is the homepage for this challenge?")
    )
    data_stored = models.BooleanField(
        default=False,
        help_text=("Has the grand-challenge team stored the data?"),
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            send_external_challenge_created_email(self)

    def get_absolute_url(self):
        return self.homepage

    @property
    def is_self_hosted(self):
        return False


@receiver(pre_delete, sender=Challenge)
@receiver(pre_delete, sender=ExternalChallenge)
def delete_challenge_follows(*_, instance: Challenge, **__):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(object_id=instance.pk, content_type=ct).delete()
