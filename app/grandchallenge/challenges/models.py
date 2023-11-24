import datetime
import logging
import math
from itertools import chain, product

from actstream.actions import follow, unfollow
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField, CICharField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    validate_slug,
)
from django.db import models
from django.db.models import ExpressionWrapper, F, OuterRef, Q, Subquery, Sum
from django.db.models.signals import post_delete, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from django_deprecate_fields import deprecate_field
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user
from machina.apps.forum.models import Forum
from machina.apps.forum_permission.models import (
    ForumPermission,
    GroupForumPermission,
    UserForumPermission,
)
from stdimage import JPEGField

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.challenges.emails import (
    send_challenge_requested_email_to_requester,
    send_challenge_requested_email_to_reviewers,
)
from grandchallenge.challenges.utils import ChallengeTypeChoices
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import (
    get_banner_path,
    get_logo_path,
    get_social_image_path,
    protected_s3_storage,
    public_s3_storage,
)
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.core.validators import (
    ExtensionValidator,
    MimeTypeValidator,
)
from grandchallenge.evaluation.tasks import assign_evaluation_permissions
from grandchallenge.evaluation.utils import (
    StatusChoices,
    SubmissionKindChoices,
)
from grandchallenge.incentives.models import Incentive
from grandchallenge.invoices.models import PaymentStatusChoices
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.pages.models import Page
from grandchallenge.publications.fields import IdentifierField
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse
from grandchallenge.task_categories.models import TaskType

logger = logging.getLogger(__name__)


class ChallengeSet(models.QuerySet):
    def with_available_compute(self):
        return self.annotate(
            approved_compute_costs_euro_millicents=(
                Sum(
                    "invoices__compute_costs_euros",
                    filter=Q(
                        invoices__payment_status__in=[
                            PaymentStatusChoices.COMPLIMENTARY,
                            PaymentStatusChoices.PAID,
                        ]
                    ),
                    output_field=models.PositiveBigIntegerField(),
                    default=0,
                )
                * 1000
                * 100
            ),
            available_compute_euro_millicents=ExpressionWrapper(
                F("approved_compute_costs_euro_millicents")
                - F("compute_cost_euro_millicents"),
                output_field=models.BigIntegerField(),
            ),
        )

    def with_most_recent_submission_datetime(self):
        from grandchallenge.evaluation.models import Submission

        latest_submission = Submission.objects.filter(
            phase__challenge=OuterRef("pk")
        ).order_by("-created")
        return self.annotate(
            most_recent_submission_datetime=Subquery(
                latest_submission.values("created")[:1]
            )
        )


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
    StatusChoices = StatusChoices

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
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
    incentives = models.ManyToManyField(
        Incentive,
        blank=True,
        help_text="What incentives are there for users to participate in this challenge?",
    )

    class Meta:
        abstract = True


class Challenge(ChallengeBase):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    description = models.CharField(
        max_length=1024,
        default="",
        blank=True,
        help_text="Short summary of this project, max 1024 characters.",
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
        help_text="Do not display this Challenge in any public overview",
    )
    educational = models.BooleanField(
        default=False, help_text="It is an educational challenge"
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
    access_request_handling = models.CharField(
        max_length=25,
        choices=AccessRequestHandlingOptions.choices,
        default=AccessRequestHandlingOptions.MANUAL_REVIEW,
        help_text=("How would you like to handle access requests?"),
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
    contact_email = models.EmailField(
        blank=True,
        default="",
        help_text="This email will be listed as the contact email for the challenge and will be visible to all users of Grand Challenge.",
    )

    accumulated_compute_cost_in_cents = deprecate_field(
        models.IntegerField(default=0, blank=True)
    )
    accumulated_docker_storage_cost_in_cents = deprecate_field(
        models.IntegerField(default=0, blank=True)
    )

    compute_cost_euro_millicents = models.PositiveBigIntegerField(
        # We store euro here as the costs were incurred at a time when
        # the exchange rate may have been different
        editable=False,
        default=0,
        help_text="The total compute cost for this challenge in Euro Cents, including Tax",
    )
    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )
    size_in_registry = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the registry",
    )

    objects = ChallengeSet.as_manager()

    class Meta:
        verbose_name = "challenge"
        verbose_name_plural = "challenges"
        ordering = ("pk",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hidden_orig = self.hidden

    def __str__(self):
        return self.short_name

    @property
    def public(self) -> bool:
        """Helper property for consistency with other objects"""
        return not self.hidden

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
    def slug(self) -> str:
        return self.short_name

    @property
    def api_url(self) -> str:
        return reverse("api:challenge-detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()
            self.create_forum()

        super().save(*args, **kwargs)

        self.assign_permissions()

        if adding:
            if self.creator:
                self.add_admin(user=self.creator)
            self.create_forum_permissions()
            self.create_default_pages()

        if adding or self.hidden != self._hidden_orig:
            on_commit(
                lambda: assign_evaluation_permissions.apply_async(
                    kwargs={
                        "phase_pks": list(
                            self.phase_set.values_list("id", flat=True)
                        )
                    }
                )
            )
            self.update_user_forum_permissions()

    def assign_permissions(self):
        # Editors and users can view this algorithm
        assign_perm("view_challenge", self.admins_group, self)
        assign_perm("view_challenge", self.participants_group, self)

        # Admins can change this challenge
        assign_perm("change_challenge", self.admins_group, self)

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm("view_challenge", reg_and_anon, self)
        else:
            remove_perm("view_challenge", reg_and_anon, self)

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
            name=settings.FORUMS_CHALLENGE_CATEGORY_NAME, type=Forum.FORUM_CAT
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
            display_title=self.short_name,
            html=render_to_string(
                "pages/defaults/home.html", {"challenge": self}
            ),
            challenge=self,
            permission_level=Page.ALL,
        )

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
            "pages:home", kwargs={"challenge_short_name": self.short_name}
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

    @cached_property
    def status(self) -> str:
        phase_status = {phase.status for phase in self.phase_set.all()}
        if StatusChoices.OPEN in phase_status:
            status = StatusChoices.OPEN
        elif {StatusChoices.COMPLETED} == phase_status:
            status = StatusChoices.COMPLETED
        elif StatusChoices.OPENING_SOON in phase_status:
            status = StatusChoices.OPENING_SOON
        else:
            status = StatusChoices.CLOSED
        return status

    @cached_property
    def should_be_open_but_is_over_budget(self):
        return self.available_compute_euro_millicents <= 0 and any(
            phase.submission_period_is_open_now
            and phase.submissions_limit_per_user_per_period > 0
            for phase in self.phase_set.all()
        )

    @cached_property
    def percent_budget_consumed(self):
        if self.approved_compute_costs_euro_millicents:
            return int(
                100
                * self.compute_cost_euro_millicents
                / self.approved_compute_costs_euro_millicents
            )
        else:
            return None

    @cached_property
    def challenge_type(self):
        phase_types = {phase.submission_kind for phase in self.phase_set.all()}
        # as long as one of the phases is type 2,
        # the challenge is classified as type 2
        if SubmissionKindChoices.ALGORITHM in phase_types:
            challenge_type = ChallengeTypeChoices.T2
        else:
            challenge_type = ChallengeTypeChoices.T1
        return challenge_type

    @property
    def status_badge_string(self):
        if self.status == StatusChoices.OPEN:
            detail = [
                phase.submission_status_string
                for phase in self.phase_set.all()
                if phase.status == StatusChoices.OPEN
            ]
            if len(detail) > 1:
                # if there are multiple open phases it is unclear which
                # status to print, so stay vague
                detail = ["Accepting submissions"]
        elif self.status == StatusChoices.COMPLETED:
            detail = ["Challenge completed"]
        elif self.status == StatusChoices.CLOSED:
            detail = ["Not accepting submissions"]
        elif self.status == StatusChoices.OPENING_SOON:
            start_date = min(
                (
                    phase.submissions_open_at
                    for phase in self.phase_set.all()
                    if phase.status == StatusChoices.OPENING_SOON
                ),
                default=None,
            )
            phase = (
                self.phase_set.filter(submissions_open_at=start_date)
                .order_by("-created")
                .first()
            )
            detail = [phase.submission_status_string]
        else:
            raise NotImplementedError(f"{self.status} not handled")

        return detail[0]

    @cached_property
    def visible_phases(self):
        # For use in list views where the phases have been prefetched
        return [phase for phase in self.phase_set.all() if phase.public]

    @cached_property
    def first_visible_phase(self):
        try:
            return self.visible_phases[0]
        except IndexError:
            return None


class ChallengeUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Challenge, on_delete=models.CASCADE)


class ChallengeGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Challenge, on_delete=models.CASCADE)


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


@receiver(pre_delete, sender=Challenge)
def delete_challenge_follows(*_, instance: Challenge, **__):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(object_id=instance.pk, content_type=ct).delete()


def submission_pdf_path(instance, filename):
    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class ChallengeRequest(UUIDModel, ChallengeBase):
    class ChallengeRequestStatusChoices(models.TextChoices):
        ACCEPTED = "ACPT", _("Accepted")
        REJECTED = "RJCT", _("Rejected")
        PENDING = "PEND", _("Pending")

    status = models.CharField(
        max_length=4,
        choices=ChallengeRequestStatusChoices.choices,
        default=ChallengeRequestStatusChoices.PENDING,
    )
    abstract = models.TextField(
        help_text="Provide a summary of the challenge purpose.",
    )
    contact_email = models.EmailField(
        help_text="Please provide an email that our team can use to contact "
        "you should there be any questions about your request.",
    )
    start_date = models.DateField(
        help_text="Estimated start date for this challenge.",
    )
    end_date = models.DateField(
        help_text="Estimated end date for this challenge. Please note that we aim to "
        "keep challenges open for submission for at least 3 years after "
        "the official end date if possible.",
    )
    organizers = models.TextField(
        help_text="Provide information about the organizing team (names and affiliations)",
    )
    affiliated_event = models.CharField(
        blank=True,
        max_length=50,
        help_text="Is this challenge part of a workshop or conference? If so, which one?",
    )
    structured_challenge_submission_form = models.FileField(
        null=True,
        blank=True,
        upload_to=submission_pdf_path,
        storage=protected_s3_storage,
        validators=[
            ExtensionValidator(allowed_extensions=(".pdf",)),
            MimeTypeValidator(allowed_types=("application/pdf",)),
        ],
    )
    challenge_setup = models.TextField(
        help_text="Describe the challenge set-up."
    )
    data_set = models.TextField(
        help_text="Describe the training and test datasets you are planning to use."
    )
    submission_assessment = models.TextField(
        help_text="Define the metrics you will use to assess and rank "
        "participants’ submissions."
    )
    challenge_publication = models.TextField(
        help_text="Please indicate if you plan to coordinate a publication "
        "of the challenge results."
    )
    code_availability = models.TextField(
        help_text="Will the participants’ code be accessible after the challenge?"
    )
    expected_number_of_teams = models.PositiveIntegerField(
        help_text="How many teams do you expect to participate in your challenge?",
        validators=[MinValueValidator(limit_value=1)],
    )
    average_algorithm_container_size_in_gb = models.PositiveIntegerField(
        default=6,
        help_text="Average algorithm container size in GB.",
        validators=[MinValueValidator(limit_value=1)],
    )
    average_number_of_containers_per_team = models.PositiveIntegerField(
        default=5,
        help_text="Average number of algorithm containers per team.",
        validators=[MinValueValidator(limit_value=1)],
    )
    inference_time_limit_in_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Average run time per algorithm job in minutes.",
        validators=[
            MinValueValidator(limit_value=1),
            MaxValueValidator(limit_value=60),
        ],
    )
    average_size_of_test_image_in_mb = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Average size of a test image in MB.",
        validators=[
            MinValueValidator(limit_value=1),
            MaxValueValidator(limit_value=10000),
        ],
    )
    phase_1_number_of_submissions_per_team = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="How many submissions do you expect per team in this phase?",
    )
    phase_2_number_of_submissions_per_team = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="How many submissions do you expect per team in this phase?",
    )
    phase_1_number_of_test_images = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of test images for this phase.",
    )
    phase_2_number_of_test_images = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of test images for this phase.",
    )
    number_of_tasks = models.PositiveIntegerField(
        default=1,
        help_text="If your challenge has multiple tasks, we multiply the "
        "phase 1 and 2 cost estimates by the number of tasks.",
        validators=[MinValueValidator(limit_value=1)],
    )
    budget_for_hosting_challenge = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="What is your budget for hosting this challenge? Please be reminded of our <a href='/challenge-policy-and-pricing/'>challenge pricing policy</a>.",
    )
    long_term_commitment = models.BooleanField(
        null=True,
        blank=True,
    )
    long_term_commitment_extra = models.CharField(
        max_length=2000,
        blank=True,
    )
    data_license = models.BooleanField(
        null=True,
        blank=True,
    )
    data_license_extra = models.CharField(
        max_length=2000,
        blank=True,
    )
    comments = models.TextField(
        blank=True,
        help_text="If you have any comments, remarks or questions, please leave them here.",
    )
    algorithm_inputs = models.TextField(
        blank=True,
        help_text="What are the inputs to the algorithms submitted as solutions to "
        "your challenge going to be? "
        "Please describe in detail "
        "what the input(s) reflect(s), for example, "
        "MRI scan of the brain, or chest X-ray. Grand Challenge only "
        "supports .mha and .tiff image files and json files for algorithms.",
    )
    algorithm_outputs = models.TextField(
        blank=True,
        help_text="What are the outputs to the algorithms submitted as solutions to "
        "your challenge going to be? "
        "Please describe in detail what the output(s) "
        "reflect(s), for example, probability of a positive PCR result, or "
        "stroke lesion segmentation. ",
    )
    structured_challenge_submission_doi = IdentifierField(
        blank=True,
        help_text="The DOI, e.g., 10.5281/zenodo.6362337, or the arXiv id, e.g., 2006.12449 of your challenge submission PDF.",
    )
    challenge_fee_agreement = models.BooleanField(
        blank=False,
        default=False,
    )

    def __str__(self):
        return self.title

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orig_status = self.status

    def get_absolute_url(self):
        return reverse("challenges:requests-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)

        if adding:
            send_challenge_requested_email_to_reviewers(self)
            send_challenge_requested_email_to_requester(self)

    def create_challenge(self):
        challenge = Challenge(
            title=self.title,
            short_name=self.short_name,
            creator=self.creator,
            hidden=True,
            contact_email=self.contact_email,
        )
        challenge.full_clean()
        challenge.save()
        challenge.task_types.set(self.task_types.all())
        challenge.modalities.set(self.modalities.all())
        challenge.structures.set(self.structures.all())
        challenge.save()

        return challenge

    @property
    def budget_fields(self):
        budget_fields = (
            "expected_number_of_teams",
            "number_of_tasks",
            "inference_time_limit_in_minutes",
            "average_size_of_test_image_in_mb",
            "phase_1_number_of_submissions_per_team",
            "phase_1_number_of_test_images",
            "phase_2_number_of_submissions_per_team",
            "phase_2_number_of_test_images",
        )
        return {
            field.verbose_name: field.value_to_string(self)
            for field in self._meta.fields
            if field.name in budget_fields
        }

    @cached_property
    def budget(self):
        if (
            self.inference_time_limit_in_minutes is not None
            and self.phase_1_number_of_test_images is not None
            and self.phase_1_number_of_submissions_per_team is not None
            and self.average_size_of_test_image_in_mb is not None
            and self.phase_2_number_of_test_images is not None
            and self.phase_2_number_of_submissions_per_team is not None
        ):
            compute_costs = settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
            s3_storage_costs = (
                settings.CHALLENGES_S3_STORAGE_COST_CENTS_PER_TB_PER_YEAR
            )
            ecr_storage_costs = (
                settings.CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR
            )
            budget = {
                "Base cost": settings.CHALLENGE_BASE_COST_IN_EURO,
                "Data storage cost for phase 1": None,
                "Compute costs for phase 1": None,
                "Total phase 1": None,
                "Data storage cost for phase 2": None,
                "Compute costs for phase 2": None,
                "Total phase 2": None,
                "Docker storage cost": None,
                "Total": None,
            }

            # calculate budget for phase 1
            budget["Data storage cost for phase 1"] = (
                math.ceil(
                    self.phase_1_number_of_test_images
                    * self.average_size_of_test_image_in_mb
                    * s3_storage_costs
                    * self.number_of_tasks
                    / 1000000
                    / 100
                    / 10,
                )
                * 10
            )
            budget["Compute costs for phase 1"] = (
                math.ceil(
                    self.phase_1_number_of_test_images
                    * self.phase_1_number_of_submissions_per_team
                    * self.expected_number_of_teams
                    * self.inference_time_limit_in_minutes
                    * compute_costs
                    * self.number_of_tasks
                    / 60
                    / 100
                    / 10,
                )
                * 10
            )
            budget["Total phase 1"] = (
                math.ceil(
                    (
                        budget["Data storage cost for phase 1"]
                        + budget["Compute costs for phase 1"]
                    )
                    / 10,
                )
                * 10
            )
            # calculate budget for phase 2
            budget["Data storage cost for phase 2"] = (
                math.ceil(
                    self.phase_2_number_of_test_images
                    * self.average_size_of_test_image_in_mb
                    * s3_storage_costs
                    * self.number_of_tasks
                    / 1000000
                    / 100
                    / 10,
                )
                * 10
            )
            budget["Compute costs for phase 2"] = (
                math.ceil(
                    self.phase_2_number_of_test_images
                    * self.phase_2_number_of_submissions_per_team
                    * self.expected_number_of_teams
                    * self.inference_time_limit_in_minutes
                    * compute_costs
                    * self.number_of_tasks
                    / 60
                    / 100
                    / 10,
                )
                * 10
            )
            budget["Total phase 2"] = (
                math.ceil(
                    (
                        budget["Data storage cost for phase 2"]
                        + budget["Compute costs for phase 2"]
                    )
                    / 10,
                )
                * 10
            )
            budget["Docker storage cost"] = (
                math.ceil(
                    self.average_algorithm_container_size_in_gb
                    * self.average_number_of_containers_per_team
                    * self.expected_number_of_teams
                    * self.number_of_tasks
                    * ecr_storage_costs
                    / 1000
                    / 100
                    / 10,
                )
                * 10
            )
            budget["Total"] = sum(
                filter(
                    None,
                    [
                        budget["Total phase 1"],
                        budget["Total phase 2"],
                        budget["Docker storage cost"],
                        budget["Base cost"],
                    ],
                )
            )
            return budget
        else:
            return None
