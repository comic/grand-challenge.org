import datetime
import hashlib
import logging
import re
from collections import namedtuple

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField, CICharField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.html import format_html
from django.utils.text import get_valid_filename
from guardian.utils import get_anonymous_user
from tldextract import extract

from grandchallenge.core.storage import public_s3_storage
from grandchallenge.subdomains.utils import reverse

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


def get_logo_path(instance, filename):
    return f"logos/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


def get_banner_path(instance, filename):
    return f"banners/{instance.pk}/{get_valid_filename(filename)}"


class TaskType(models.Model):
    """Stores the task type options, eg, Segmentation, Regression, etc."""

    type = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("type",)

    def __str__(self):
        return self.type

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.type)
        return f"task-{cls}"

    @property
    def badge(self):
        return format_html(
            '<span class="badge badge-light" title="{0} challenge">'
            '<i class="fas fa-tasks fa-fw"></i> {0}</span>',
            self.type,
        )


class ImagingModality(models.Model):
    """Store the modality options, eg, MR, CT, PET, XR."""

    modality = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("modality",)

    def __str__(self):
        return self.modality

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.modality)
        return f"modality-{cls}"

    @property
    def badge(self):
        return format_html(
            '<span class="badge badge-secondary" title="Uses {0} data">'
            '<i class="fas fa-microscope fa-fw"></i> {0}</span>',
            self.modality,
        )


class BodyRegion(models.Model):
    """Store the anatomy options, eg, Head, Neck, Thorax, etc."""

    region = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("region",)

    def __str__(self):
        return self.region

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.region)
        return f"region-{cls}"


class BodyStructure(models.Model):
    """Store the organ name and what region it belongs to."""

    structure = CICharField(max_length=16, blank=False, unique=True)
    region = models.ForeignKey(
        to=BodyRegion, on_delete=models.CASCADE, blank=False
    )

    class Meta:
        ordering = ("region", "structure")

    def __str__(self):
        return f"{self.structure} ({self.region})"

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.structure)
        return f"structure-{cls}"

    @property
    def badge(self):
        return format_html(
            '<span class="badge badge-dark" title="Uses {0} data">'
            '<i class="fas fa-child fa-fw"></i> {0}</span>',
            self.structure,
        )


class ChallengeSeries(models.Model):
    name = CICharField(max_length=64, blank=False, unique=True)
    url = models.URLField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "Challenge Series"

    def __str__(self):
        return f"{self.name}"

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.name)
        return f"series-{cls}"

    @property
    def badge(self):
        return format_html(
            '<span class="badge badge-info" title="Associated with {0}">'
            '<i class="fas fa-globe fa-fw"></i> {0}</span>',
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
    logo = models.ImageField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        blank=True,
        help_text="A logo for this challenge. Should be square with a resolution of 640x640 px or higher.",
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
    publication_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL of a publication describing this project",
    )
    publication_journal_name = models.CharField(
        max_length=225,
        blank=True,
        null=True,
        help_text=(
            "If publication was in a journal, please list the journal name "
            "here We use <a target='new' "
            "href='https://www.ncbi.nlm.nih.gov/nlmcatalog/journals'>PubMed "
            "journal abbreviations</a> format"
        ),
    )
    publication_citation_count = models.PositiveIntegerField(
        blank=True,
        default=0,
        help_text="The number of citations for the publication",
    )
    publication_google_scholar_id = models.BigIntegerField(
        blank=True,
        null=True,
        help_text=(
            "The ID of the article in google scholar. For instance, setting "
            "this to 5362332738201102290, which the ID for LeCun et al. "
            "in Nature 2015, and corresponds to the url"
            "https://scholar.google.com/scholar?cluster=5362332738201102290"
        ),
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

    number_of_training_cases = models.IntegerField(blank=True, null=True)
    number_of_test_cases = models.IntegerField(blank=True, null=True)
    filter_classes = ArrayField(
        CICharField(max_length=32), default=list, editable=False
    )

    objects = ChallengeManager()

    def __str__(self):
        return self.short_name

    @property
    def gravatar_url(self):
        return (
            "https://www.gravatar.com/avatar/"
            f"{hashlib.md5(self.creator.email.lower().encode()).hexdigest()}"
            "?s=320"
        )

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

    def get_filter_classes(self):
        """
        Warning! Do not call this directly, it takes a while. This is used
        in a background task.
        """
        classes = set()

        if self.host_filter.host:
            classes.add(self.host_filter.filter_tag)

        # Filter by modality
        for mod in self.modalities.all():
            classes.add(mod.filter_tag)

        # Filter by body region and structure
        for struc in self.structures.all():
            classes.add(struc.region.filter_tag)
            classes.add(struc.filter_tag)

        # Filter by task type
        for tas in self.task_types.all():
            classes.add(tas.filter_tag)

        # Filter by challenge series
        for series in self.series.all():
            classes.add(series.filter_tag)

        if self.educational:
            classes.add("educational")

        classes.add(f"year-{self.year}")

        return list(classes)

    @property
    def host_filter(self):
        host_filter = namedtuple("host_filter", ["host", "filter_tag"])
        domain = self.registered_domain
        return host_filter(domain, re.sub(r"\W+", "", domain))

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


class Challenge(ChallengeBase):
    """
    A collection of HTML pages using a certain skin. Pages can be browsed and
    edited.
    """

    public_folder = "public_html"
    skin = models.TextField(
        default="", blank=True, help_text="CSS for this challenge.",
    )
    banner = models.ImageField(
        upload_to=get_banner_path,
        storage=public_s3_storage,
        blank=True,
        help_text=(
            "Image that gets displayed at the top of each page. "
            "Recommended resolution 2200x440 px."
        ),
    )
    hide_signin = models.BooleanField(
        default=False,
        help_text="Do no show the Sign in / Register link on any page",
    )
    hide_footer = models.BooleanField(
        default=False,
        help_text=(
            "Do not show the general links or "
            "the grey divider line in page footers"
        ),
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
    use_evaluation = models.BooleanField(
        default=False,
        help_text=(
            "If true, use the automated evaluation system. See the evaluation "
            "page created in the Challenge site."
        ),
    )
    admins_group = models.OneToOneField(
        Group,
        null=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name="admins_of_challenge",
    )
    participants_group = models.OneToOneField(
        Group,
        null=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name="participants_of_challenge",
    )

    cached_num_participants = models.PositiveIntegerField(
        editable=False, default=0
    )
    cached_num_results = models.PositiveIntegerField(editable=False, default=0)
    cached_latest_result = models.DateTimeField(
        editable=False, blank=True, null=True
    )

    def admin_group_name(self):
        """Return the name of this challenges admin group."""
        return self.short_name + "_admins"

    def participants_group_name(self):
        """Return the name of the participants group."""
        return self.short_name + "_participants"

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
        else:
            raise ValueError("You cannot add the anonymous user to this group")

    def remove_participant(self, user):
        user.groups.remove(self.participants_group)

    def add_admin(self, user):
        if user != get_anonymous_user():
            user.groups.add(self.admins_group)
        else:
            raise ValueError("You cannot add the anonymous user to this group")

    def remove_admin(self, user):
        user.groups.remove(self.admins_group)

    class Meta:
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

    def get_absolute_url(self):
        return self.homepage

    @property
    def is_self_hosted(self):
        return False
