import datetime
import logging
import math

from actstream.actions import follow, unfollow
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator, validate_slug
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    Count,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.signals import post_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.timezone import now, timedelta
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user
from stdimage import JPEGField

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.challenges.emails import (
    send_challenge_requested_email_to_requester,
    send_challenge_requested_email_to_reviewers,
    send_email_percent_budget_consumed_alert,
)
from grandchallenge.challenges.utils import ChallengeTypeChoices
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
    filter_by_permission,
)
from grandchallenge.core.models import FieldChangeMixin, UUIDModel
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
    JSONValidator,
    MimeTypeValidator,
)
from grandchallenge.discussion_forums import models as discussion_forum_models
from grandchallenge.evaluation.tasks import assign_evaluation_permissions
from grandchallenge.evaluation.utils import (
    StatusChoices,
    SubmissionKindChoices,
)
from grandchallenge.incentives.models import Incentive
from grandchallenge.invoices.models import (
    PaymentStatusChoices,
    PaymentTypeChoices,
)
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
            complimentary_compute_costs_euros=(
                Sum(
                    "invoices__compute_costs_euros",
                    filter=Q(
                        invoices__payment_type=PaymentTypeChoices.COMPLIMENTARY
                    ),
                    output_field=models.PositiveBigIntegerField(),
                    default=0,
                )
            ),
            prepaid_compute_costs_euros=(
                Sum(
                    "invoices__compute_costs_euros",
                    filter=Q(
                        invoices__payment_type=PaymentTypeChoices.PREPAID,
                        invoices__payment_status=PaymentStatusChoices.PAID,
                    ),
                    output_field=models.PositiveBigIntegerField(),
                    default=0,
                )
            ),
            postpaid_compute_costs_euros_if_anything_paid=(
                Case(
                    When(
                        prepaid_compute_costs_euros__gt=0,
                        then=Sum(
                            "invoices__compute_costs_euros",
                            filter=Q(
                                invoices__payment_type=PaymentTypeChoices.POSTPAID
                            )
                            & ~Q(
                                invoices__payment_status=PaymentStatusChoices.CANCELLED
                            ),
                            output_field=models.PositiveBigIntegerField(),
                            default=0,
                        ),
                    ),
                    default=0,
                    output_field=models.PositiveBigIntegerField(),
                )
            ),
            approved_compute_costs_euro_millicents=ExpressionWrapper(
                (
                    F("complimentary_compute_costs_euros")
                    + F("prepaid_compute_costs_euros")
                    + F("postpaid_compute_costs_euros_if_anything_paid")
                )
                * 1000
                * 100,
                output_field=models.PositiveBigIntegerField(),
            ),
            available_compute_euro_millicents=ExpressionWrapper(
                F("approved_compute_costs_euro_millicents")
                - F("compute_cost_euro_millicents"),
                output_field=models.BigIntegerField(),
            ),
        )


def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError("Underscores (_) are not allowed.")


def validate_short_name(value):
    if value.lower() in settings.DISALLOWED_CHALLENGE_NAMES:
        raise ValidationError("That name is not allowed.")

    if Challenge.objects.filter(short_name__iexact=value).exists():
        raise ValidationError("Challenge with this slug already exists")


class ChallengeSeries(models.Model):
    name = models.CharField(max_length=64, blank=False, unique=True)
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
    short_name = models.CharField(
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


def get_default_percent_budget_consumed_warning_thresholds():
    return [70, 90, 100]


class Challenge(ChallengeBase, FieldChangeMixin):
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
    is_suspended = models.BooleanField(
        default=False,
        help_text="Challenge is suspended and not accepting submissions",
    )
    is_active_until = models.DateField(
        help_text="The date at which the challenge becomes inactive",
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
    registration_page_markdown = models.TextField(
        blank=True,
        help_text=(
            "Markdown to include on the registration page to provide "
            "more context to users registering for the challenge."
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
    external_evaluators_group = models.OneToOneField(
        Group,
        editable=False,
        on_delete=models.PROTECT,
        related_name="external_evaluators_of_challenge",
    )
    discussion_forum = models.OneToOneField(
        discussion_forum_models.Forum,
        related_name="linked_challenge",
        null=True,
        editable=False,
        on_delete=models.PROTECT,
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

    percent_budget_consumed_warning_thresholds = models.JSONField(
        default=get_default_percent_budget_consumed_warning_thresholds,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "exclusiveMinimum": 0,
                        "maximum": 100,
                    },
                    "uniqueItems": True,
                }
            )
        ],
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
        permissions = [
            ("add_registration_question", "Can add registration questions"),
        ]

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

    @cached_property
    def is_active(self):
        return today().date() < self.is_active_until

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()
            self.create_forum()
            self.is_active_until = today().date() + relativedelta(
                months=settings.CHALLENGES_DEFAULT_ACTIVE_MONTHS
            )

        super().save(*args, **kwargs)

        self.assign_permissions()

        if adding:
            if self.creator:
                self.add_admin(user=self.creator)
            self.create_default_pages()
            self.create_default_onboarding_tasks()

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

        if self.has_changed("compute_cost_euro_millicents"):
            self.send_alert_if_budget_consumed_warning_threshold_exceeded()

    def assign_permissions(self):
        # Editors and users can view this challenge
        assign_perm("view_challenge", self.admins_group, self)
        assign_perm("view_challenge", self.participants_group, self)

        # Admins can change this challenge
        assign_perm("change_challenge", self.admins_group, self)

        # Admin can add registration questions
        assign_perm("add_registration_question", self.admins_group, self)

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm("view_challenge", reg_and_anon, self)
        else:
            remove_perm("view_challenge", reg_and_anon, self)

        self.assign_discussion_forum_permissions()

    def assign_discussion_forum_permissions(self):
        if self.display_forum_link:
            assign_perm(
                "discussion_forums.view_forum",
                self.admins_group,
                self.discussion_forum,
            )
            assign_perm(
                "discussion_forums.view_forum",
                self.participants_group,
                self.discussion_forum,
            )
            assign_perm(
                "discussion_forums.create_forum_topic",
                self.admins_group,
                self.discussion_forum,
            )
            assign_perm(
                "discussion_forums.create_forum_topic",
                self.participants_group,
                self.discussion_forum,
            )
            assign_perm(
                "discussion_forums.create_sticky_and_announcement_topic",
                self.admins_group,
                self.discussion_forum,
            )
        else:
            remove_perm(
                "discussion_forums.view_forum",
                self.admins_group,
                self.discussion_forum,
            )
            remove_perm(
                "discussion_forums.view_forum",
                self.participants_group,
                self.discussion_forum,
            )
            remove_perm(
                "discussion_forums.create_forum_topic",
                self.admins_group,
                self.discussion_forum,
            )
            remove_perm(
                "discussion_forums.create_forum_topic",
                self.participants_group,
                self.discussion_forum,
            )
            remove_perm(
                "discussion_forums.create_sticky_and_announcement_topic",
                self.admins_group,
                self.discussion_forum,
            )

    def create_groups(self):
        # Create the groups only on first save
        admins_group = Group.objects.create(name=f"{self.short_name}_admins")
        participants_group = Group.objects.create(
            name=f"{self.short_name}_participants"
        )
        external_evaluators_group = Group.objects.create(
            name=f"{self.short_name}_external_evaluators"
        )
        self.admins_group = admins_group
        self.participants_group = participants_group
        self.external_evaluators_group = external_evaluators_group

    def create_forum(self):
        self.discussion_forum = discussion_forum_models.Forum.objects.create()

    def create_default_pages(self):
        Page.objects.create(
            display_title=self.short_name,
            content_markdown=render_to_string(
                "pages/defaults/home.md", {"challenge": self}
            ),
            challenge=self,
            permission_level=Page.ALL,
        )

    def create_default_onboarding_tasks(self):
        OnboardingTask.objects.create(
            challenge=self,
            title="Create Phases",
            description="Create and configure the different phases of the challenge.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=1),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Define Inputs and Outputs",
            description=format_html(
                "E-mail {support_email} and communicate the required input and output data formats for participant's algorithms.",
                support_email=settings.SUPPORT_EMAIL,
            ),
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=2),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Plan Onboarding Meeting",
            description="Create a Challenge Pack and have an onboarding meeting with challenge organizers.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
            deadline=self.created + timedelta(weeks=2),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Have Onboarding Meeting",
            description="Receive a Challenge Pack and have an onboarding meeting with support staff.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=3),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Create Archives",
            description="Create an archive per algorithm-type phase for the challenge.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
            deadline=self.created + timedelta(weeks=3),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Upload Data to Archives",
            description=format_html(
                "Add data to the relevant archives. Archives must be created by support. Please e-mail {support_email} if that is delayed.",
                support_email=settings.SUPPORT_EMAIL,
            ),
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=5),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Create Example Algorithm",
            description="Implement and document a baseline example algorithm for participants to use as a reference. "
            "Use the provided challenge pack as a starting point.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=6, seconds=0),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Create Evaluation Method",
            description="Implement and document the evaluation method for assessing participant submissions. "
            "Use the provided challenge pack as a starting point.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=6, seconds=1),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Configure Scoring",
            description="Configure the leaderboard scoring to accurately interpret the evaluation results.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=6, seconds=2),
        )
        OnboardingTask.objects.create(
            challenge=self,
            title="Test Evaluation",
            description="Run test evaluations using sample submissions to ensure the scoring system and "
            "evaluation method function correctly before launching the challenge.",
            responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
            deadline=self.created + timedelta(weeks=6, seconds=3),
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
                user=user,
                obj=self.discussion_forum,
                actor_only=False,
                send_action=False,
            )
        else:
            raise ValueError("You cannot add the anonymous user to this group")

    def remove_participant(self, user):
        user.groups.remove(self.participants_group)
        unfollow(user=user, obj=self.discussion_forum, send_action=False)

    def add_admin(self, user):
        if user != get_anonymous_user():
            user.groups.add(self.admins_group)
            follow(
                user=user,
                obj=self.discussion_forum,
                actor_only=False,
                send_action=False,
            )
        else:
            raise ValueError("You cannot add the anonymous user to this group")

    def remove_admin(self, user):
        user.groups.remove(self.admins_group)
        unfollow(user=user, obj=self.discussion_forum, send_action=False)

    @cached_property
    def status(self) -> str:
        phase_status = {phase.status for phase in self.visible_phases}

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

    def send_alert_if_budget_consumed_warning_threshold_exceeded(self):
        for percent_threshold in sorted(
            self.percent_budget_consumed_warning_thresholds, reverse=True
        ):
            previous_cost = self.initial_value("compute_cost_euro_millicents")
            threshold = (
                self.approved_compute_costs_euro_millicents
                * percent_threshold
                / 100
            )
            current_cost = self.compute_cost_euro_millicents
            if previous_cost <= threshold < current_cost:
                send_email_percent_budget_consumed_alert(
                    self, percent_threshold
                )
                break

    @cached_property
    def challenge_type(self):
        phase_types = {phase.submission_kind for phase in self.visible_phases}

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
                for phase in self.visible_phases
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
                    for phase in self.visible_phases
                    if phase.status == StatusChoices.OPENING_SOON
                ),
                default=None,
            )
            phase = (
                self.phase_set.filter(
                    submissions_open_at=start_date,
                    public=True,
                )
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
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Challenge, on_delete=models.CASCADE)


class ChallengeGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_challenge", "add_registration_question", "view_challenge"}
    )

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

    try:
        instance.external_evaluators_group.delete(using=using)
    except ObjectDoesNotExist:
        pass


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
    number_of_teams_for_phases = models.JSONField(
        help_text="Number of teams for each phase",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 1,
                    },
                }
            )
        ],
    )
    average_algorithm_container_size_in_gb = models.PositiveIntegerField(
        default=6,
        help_text="Average algorithm container size in GB.",
        validators=[MinValueValidator(limit_value=1)],
    )
    inference_time_average_minutes_for_tasks = models.JSONField(
        help_text="Average run time per algorithm job in minutes, for each task.",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 5,
                        "maximum": 60,
                    },
                }
            )
        ],
    )
    algorithm_selectable_gpu_type_choices_for_tasks = models.JSONField(
        default=list,
        help_text=(
            "The GPU type choices that participants will be able to select for their "
            "algorithm inference jobs, for each task. Options are "
            f"{GPUTypeChoices.values}.".replace("'", '"')
        ),
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "title": "The Selectable GPU Types Schema",
                    "items": {
                        "type": "array",
                        "items": {
                            "enum": GPUTypeChoices.values,
                            "type": "string",
                        },
                        "uniqueItems": True,
                    },
                }
            )
        ],
    )
    algorithm_maximum_settable_memory_gb_for_tasks = models.JSONField(
        default=list,
        help_text=(
            "Maximum amount of main memory (DRAM) that participants will be allowed to "
            "assign to algorithm inference jobs for submission."
        ),
    )
    average_size_test_image_mb_for_tasks = models.JSONField(
        help_text="Average size of a test image in MB, for each task.",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10000,
                    },
                }
            )
        ],
    )
    number_of_submissions_per_team_for_phases = models.JSONField(
        help_text="Number of submissions per team for each phase",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 1,
                    },
                }
            )
        ],
    )
    number_of_test_images_for_phases = models.JSONField(
        help_text="Number of test images for each phase.",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 1,
                    },
                }
            )
        ],
    )
    task_ids = models.JSONField(
        help_text="List the task id's, e.g. [1, 2, 3].",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                    "uniqueItems": True,
                }
            )
        ],
    )
    task_id_for_phases = models.JSONField(
        help_text="Indicate which phase belongs to which task, e.g. [1, 1, 2, 2] means the first two phases below to task 1, the last two phases below to task 2.",
        default=list,
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                }
            )
        ],
    )
    data_license = models.BooleanField(
        default=False,
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
        help_text="What are the inputs to the algorithms submitted as solutions to "
        "your challenge going to be? "
        "Please describe in detail "
        "what the input(s) reflect(s), for example, "
        "MRI scan of the brain, or chest X-ray. Grand Challenge only "
        "supports .mha and .tiff image files and json files for algorithms.",
    )
    algorithm_outputs = models.TextField(
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
            self.assign_permissions()
            send_challenge_requested_email_to_reviewers(self)
            send_challenge_requested_email_to_requester(self)

    def assign_permissions(self):
        assign_perm("view_challengerequest", self.creator, self)
        reviewers = Group.objects.get(
            name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
        )
        assign_perm("view_challengerequest", reviewers, self)
        assign_perm("change_challengerequest", reviewers, self)

    def create_challenge(self):
        challenge = Challenge(
            title=self.title,
            short_name=self.short_name,
            creator=self.creator,
            hidden=True,
            contact_email=self.contact_email,
            is_active_until=(
                today().date()
                + relativedelta(
                    months=settings.CHALLENGES_DEFAULT_ACTIVE_MONTHS
                )
            ),
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
        budget_fields = {}
        for field_name in (
            "task_ids",
            "algorithm_selectable_gpu_type_choices_for_tasks",
            "algorithm_maximum_settable_memory_gb_for_tasks",
            "average_size_test_image_mb_for_tasks",
            "inference_time_average_minutes_for_tasks",
            "task_id_for_phases",
            "number_of_teams_for_phases",
            "number_of_submissions_per_team_for_phases",
            "number_of_test_images_for_phases",
        ):
            field = self._meta.get_field(field_name)
            budget_fields[field.verbose_name] = field.value_to_string(self)
        return budget_fields

    @cached_property
    def task_index_for_phases(self):
        return [
            self.task_ids.index(task_id) for task_id in self.task_id_for_phases
        ]

    @cached_property
    def inference_time_average_minutes_for_phases(self):
        return [
            self.inference_time_average_minutes_for_tasks[task_index]
            for task_index in self.task_index_for_phases
        ]

    @cached_property
    def average_size_test_image_mb_for_phases(self):
        return [
            self.average_size_test_image_mb_for_tasks[task_index]
            for task_index in self.task_index_for_phases
        ]

    @cached_property
    def number_of_submissions_for_phases(self):
        return [
            n_submissions * n_teams
            for n_submissions, n_teams in zip(
                self.number_of_submissions_per_team_for_phases,
                self.number_of_teams_for_phases,
                strict=True,
            )
        ]

    @property
    def total_number_of_submissions(self):
        return sum(self.number_of_submissions_for_phases)

    @cached_property
    def number_of_algorithm_jobs_for_phases(self):
        return [
            n_submissions * n_images
            for n_submissions, n_images in zip(
                self.number_of_submissions_for_phases,
                self.number_of_test_images_for_phases,
                strict=True,
            )
        ]

    @cached_property
    def compute_time_for_phases(self):
        return [
            n_jobs * datetime.timedelta(minutes=average_minutes)
            for n_jobs, average_minutes in zip(
                self.number_of_algorithm_jobs_for_phases,
                self.inference_time_average_minutes_for_phases,
                strict=True,
            )
        ]

    @property
    def total_compute_time(self):
        return sum(self.compute_time_for_phases, timedelta(0))

    @cached_property
    def data_storage_size_gb_for_phases(self):
        return [
            n_images * image_mb * settings.MEGABYTE / settings.GIGABYTE
            for n_images, image_mb in zip(
                self.number_of_test_images_for_phases,
                self.average_size_test_image_mb_for_phases,
                strict=True,
            )
        ]

    @property
    def number_of_docker_images_per_team_for_tasks(self):
        # A docker image for a later phase should also be submitted to an earlier one.
        return [
            self.number_of_submissions_per_team_for_phases[
                self.task_id_for_phases.index(task_id)
            ]
            for task_id in self.task_ids
        ]

    @property
    def number_of_teams_for_tasks(self):
        return [
            self.number_of_teams_for_phases[
                self.task_id_for_phases.index(task_id)
            ]
            for task_id in self.task_ids
        ]

    @property
    def number_of_docker_images_for_tasks(self):
        # A docker image for a later phase should also be submitted to an earlier one.
        return [
            self.number_of_submissions_for_phases[
                self.task_id_for_phases.index(task_id)
            ]
            for task_id in self.task_ids
        ]

    @property
    def docker_storage_size_gb_for_tasks(self):
        return [
            self.average_algorithm_container_size_in_gb
            * number_of_docker_images
            for number_of_docker_images in self.number_of_docker_images_for_tasks
        ]

    @property
    def total_number_of_docker_images(self):
        # A docker for a later phase should also be submitted to an earlier one.
        return sum(self.number_of_docker_images_for_tasks)

    @property
    def total_docker_storage_size_gb(self):
        return (
            self.average_algorithm_container_size_in_gb
            * self.total_number_of_docker_images
        )

    @property
    def total_data_and_docker_storage_gb(self):
        return self.total_docker_storage_size_gb + sum(
            self.data_storage_size_gb_for_phases
        )

    @property
    def total_data_and_docker_storage_bytes(self):
        return self.total_data_and_docker_storage_gb * settings.GIGABYTE

    @staticmethod
    def round_to_cents(euros):
        return math.ceil(euros * 100) / 100

    @cached_property
    def compute_costs_euros_per_hour_for_tasks(self):
        Executor = import_string(  # noqa: N806
            settings.COMPONENTS_DEFAULT_BACKEND
        )
        costs_for_tasks = []
        for gpu_choices, max_memory_gb, average_time in zip(
            self.algorithm_selectable_gpu_type_choices_for_tasks,
            self.algorithm_maximum_settable_memory_gb_for_tasks,
            self.inference_time_average_minutes_for_tasks,
            strict=True,
        ):
            executors = [
                Executor(
                    job_id="",
                    exec_image_repo_tag="",
                    memory_limit=max_memory_gb,
                    time_limit=average_time,
                    requires_gpu_type=gpu_type,
                    use_warm_pool=False,
                    signing_key=b"",
                )
                for gpu_type in gpu_choices
            ]
            usd_cents_per_hour = max(
                executor.usd_cents_per_hour for executor in executors
            )
            costs_for_tasks.append(
                usd_cents_per_hour * settings.COMPONENTS_USD_TO_EUR / 100
            )
        return costs_for_tasks

    @cached_property
    def compute_costs_euros_per_hour_for_phases(self):
        return [
            self.compute_costs_euros_per_hour_for_tasks[task_index]
            for task_index in self.task_index_for_phases
        ]

    @property
    def storage_costs_euros_per_gb(self):
        return (
            settings.CHALLENGE_NUM_SUPPORT_YEARS
            * settings.COMPONENTS_S3_USD_MILLICENTS_PER_YEAR_PER_TB_EXCLUDING_TAX
            * (1 + settings.COMPONENTS_TAX_RATE)
            * settings.COMPONENTS_USD_TO_EUR
            / 1000
            / 100
            / settings.TERABYTE
            * settings.GIGABYTE
        )

    @cached_property
    def compute_costs_euros_for_phases(self):
        return [
            self.round_to_cents(
                compute_costs_euros_per_hour
                * compute_time.total_seconds()
                / 3600
            )
            for compute_time, compute_costs_euros_per_hour in zip(
                self.compute_time_for_phases,
                self.compute_costs_euros_per_hour_for_phases,
                strict=True,
            )
        ]

    @cached_property
    def data_storage_costs_euros_for_phases(self):
        return [
            self.round_to_cents(self.storage_costs_euros_per_gb * size_gb)
            for size_gb in self.data_storage_size_gb_for_phases
        ]

    @cached_property
    def compute_and_storage_costs_euros_for_phases(self):
        return [
            compute_costs + data_storage_costs
            for compute_costs, data_storage_costs in zip(
                self.compute_costs_euros_for_phases,
                self.data_storage_costs_euros_for_phases,
                strict=True,
            )
        ]

    @cached_property
    def compute_costs_euros_for_tasks(self):
        return [
            sum(
                [
                    self.compute_costs_euros_for_phases[phase_index]
                    for phase_index, task_id_phase in enumerate(
                        self.task_id_for_phases
                    )
                    if task_id_phase == task_id
                ]
            )
            for task_id in self.task_ids
        ]

    @cached_property
    def data_storage_costs_euros_for_tasks(self):
        return [
            sum(
                [
                    self.data_storage_costs_euros_for_phases[phase_index]
                    for phase_index, task_id_phase in enumerate(
                        self.task_id_for_phases
                    )
                    if task_id_phase == task_id
                ]
            )
            for task_id in self.task_ids
        ]

    @property
    def docker_storage_costs_euros_for_tasks(self):
        return [
            self.round_to_cents(self.storage_costs_euros_per_gb * size_gb)
            for size_gb in self.docker_storage_size_gb_for_tasks
        ]

    @property
    def storage_costs_euros_for_tasks(self):
        return [
            docker_storage_costs_euros + data_storage_costs_euros
            for docker_storage_costs_euros, data_storage_costs_euros in zip(
                self.docker_storage_costs_euros_for_tasks,
                self.data_storage_costs_euros_for_tasks,
                strict=True,
            )
        ]

    @property
    def compute_and_storage_costs_euros_for_tasks(self):
        return [
            storage_costs_euros + compute_costs_euros
            for storage_costs_euros, compute_costs_euros in zip(
                self.storage_costs_euros_for_tasks,
                self.compute_costs_euros_for_tasks,
                strict=True,
            )
        ]

    @property
    def total_compute_costs_euros(self):
        return sum(self.compute_costs_euros_for_phases)

    @property
    def total_docker_storage_costs_euros(self):
        return sum(self.docker_storage_costs_euros_for_tasks)

    @property
    def total_storage_costs_euros(self):
        return self.total_docker_storage_costs_euros + sum(
            self.data_storage_costs_euros_for_phases
        )

    @property
    def total_compute_and_storage_costs_euros(self):
        return self.total_storage_costs_euros + self.total_compute_costs_euros

    @property
    def capacity_reservation_units(self):
        return math.ceil(
            max(
                settings.CHALLENGE_MINIMAL_COMPUTE_AND_STORAGE_IN_EURO,
                self.total_compute_and_storage_costs_euros,
            )
            / settings.CHALLENGE_CAPACITY_RESERVATION_PACK_SIZE_IN_EURO
        )

    @property
    def capacity_reservation_euros(self):
        return (
            self.capacity_reservation_units
            * settings.CHALLENGE_CAPACITY_RESERVATION_PACK_SIZE_IN_EURO
        )

    @cached_property
    def base_cost_euros(self):
        if (
            self.creator
            and Organization.objects.filter(
                exempt_from_base_costs=True, members_group__user=self.creator
            ).exists()
        ):
            return 0
        else:
            return settings.CHALLENGE_BASE_COST_IN_EURO

    @property
    def total_challenge_price(self):
        return self.base_cost_euros + self.capacity_reservation_euros

    @property
    def costs_for_tasks(self):
        return [
            {
                "id": task_id,
                "costs_for_phases_in_task": self.get_costs_for_phases_in_task(
                    task_id
                ),
                "number_of_docker_images_per_team": self.number_of_docker_images_per_team_for_tasks[
                    task_index
                ],
                "number_of_teams": self.number_of_teams_for_tasks[task_index],
                "docker_storage_size_gb": self.docker_storage_size_gb_for_tasks[
                    task_index
                ],
                "docker_storage_costs_euros": self.docker_storage_costs_euros_for_tasks[
                    task_index
                ],
                "inference_time_average_minutes": self.inference_time_average_minutes_for_tasks[
                    task_index
                ],
                "compute_costs_euros_per_hour": self.compute_costs_euros_per_hour_for_tasks[
                    task_index
                ],
                "average_size_test_image_mb": self.average_size_test_image_mb_for_tasks[
                    task_index
                ],
                "compute_costs_euros": self.compute_costs_euros_for_tasks[
                    task_index
                ],
                "storage_costs_euros": self.storage_costs_euros_for_tasks[
                    task_index
                ],
                "compute_and_storage_costs_euros": self.compute_and_storage_costs_euros_for_tasks[
                    task_index
                ],
            }
            for task_index, task_id in enumerate(self.task_ids)
        ]

    def get_costs_for_phases_in_task(self, task_id):
        phase_indices = [
            idx
            for idx, val in enumerate(self.task_id_for_phases)
            if val == task_id
        ]
        return [
            {
                "number_of_submissions_per_team": self.number_of_submissions_per_team_for_phases[
                    phase_index
                ],
                "number_of_teams": self.number_of_teams_for_phases[
                    phase_index
                ],
                "number_of_test_images": self.number_of_test_images_for_phases[
                    phase_index
                ],
                "compute_time": self.compute_time_for_phases[phase_index],
                "data_storage_size_gb": self.data_storage_size_gb_for_phases[
                    phase_index
                ],
                "compute_costs_euros": self.compute_costs_euros_for_phases[
                    phase_index
                ],
                "data_storage_costs_euros": self.data_storage_costs_euros_for_phases[
                    phase_index
                ],
                "compute_and_storage_costs_euros": self.compute_and_storage_costs_euros_for_phases[
                    phase_index
                ],
            }
            for phase_index in phase_indices
        ]

    @property
    def capacity_reservation_compute_euros(self):
        return (
            self.total_compute_costs_euros
            / self.total_compute_and_storage_costs_euros
            * self.capacity_reservation_euros
        )

    @property
    def capacity_reservation_storage_euros(self):
        return (
            self.total_storage_costs_euros
            / self.total_compute_and_storage_costs_euros
            * self.capacity_reservation_euros
        )


class ChallengeRequestUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"view_challengerequest"})

    content_object = models.ForeignKey(
        ChallengeRequest, on_delete=models.CASCADE
    )


class ChallengeRequestGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"view_challengerequest", "change_challengerequest"}
    )

    content_object = models.ForeignKey(
        ChallengeRequest, on_delete=models.CASCADE
    )


class TaskResponsiblePartyChoices(models.TextChoices):
    SUPPORT = "SUP", "Support"
    CHALLENGE_ORGANIZERS = "ORG", "Challenge Organizers"


class OnboardingTaskQuerySet(models.QuerySet):
    def with_overdue_status(self):

        _now = now()
        return self.annotate(
            is_overdue=Case(
                When(complete=False, deadline__lt=_now, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            is_overdue_soon=Case(
                When(
                    complete=False,
                    is_overdue=False,
                    deadline__lt=_now
                    + settings.CHALLENGE_ONBOARDING_TASKS_OVERDUE_SOON_CUTOFF,
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )

    def updatable_by(self, user):
        return filter_by_permission(
            queryset=self,
            user=user,
            codename="change_onboardingtask",
        )

    @property
    def status_aggregates(self):
        return self.aggregate(
            num_is_overdue=Count("pk", filter=Q(is_overdue=True)),
            num_is_overdue_soon=Count("pk", filter=Q(is_overdue_soon=True)),
        )


class OnboardingTask(FieldChangeMixin, UUIDModel):
    ResponsiblePartyChoices = TaskResponsiblePartyChoices

    objects = OnboardingTaskQuerySet.as_manager()

    created = models.DateTimeField(editable=False)
    challenge = models.ForeignKey(
        to=Challenge,
        on_delete=models.CASCADE,
        related_name="onboarding_tasks",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of this task",
    )

    description = models.TextField(
        blank=True, help_text="Description of this task."
    )
    complete = models.BooleanField(
        default=False,
        help_text="If true, this task is complete.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time this task was last marked completed.",
    )
    responsible_party = models.CharField(
        blank=False,
        max_length=3,
        choices=ResponsiblePartyChoices.choices,
        default=ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
        help_text="Who is responsible for completion of this task.",
    )
    deadline = models.DateTimeField(
        help_text="Deadline for this task.",
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        _now = now()

        if adding:
            self.created = _now
        if self.complete and (self.has_changed("complete") or adding):
            self.completed_at = _now

        super().save(*args, **kwargs)

        self.assign_permissions()

    def assign_permissions(self):
        if (
            self.responsible_party
            == self.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS
        ):
            assign_perm(
                "change_onboardingtask", self.challenge.admins_group, self
            )
            assign_perm(
                "view_onboardingtask", self.challenge.admins_group, self
            )
        else:
            remove_perm(
                "change_onboardingtask", self.challenge.admins_group, self
            )
            remove_perm(
                "view_onboardingtask", self.challenge.admins_group, self
            )


class OnboardingTaskUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE
    )


class OnboardingTaskGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_onboardingtask", "view_onboardingtask"}
    )

    content_object = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE
    )
