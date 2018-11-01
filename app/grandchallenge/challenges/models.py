import datetime
import hashlib
import logging
import os
import re

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import CICharField, ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.utils._os import safe_join
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user

from grandchallenge.core.urlresolvers import reverse

logger = logging.getLogger("django")


class ChallengeManager(models.Manager):
    """ adds some tabel level functions for getting ComicSites from db. """

    def non_hidden(self):
        """ like all(), but only return ComicSites for which hidden=false"""
        return self.filter(hidden=False)


def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError(
            "underscores not allowed. The url \
            '{}.{}' would not be valid, "
            "please use hyphens (-)".format(value, settings.MAIN_PROJECT_NAME)
        )


def validate_short_name(value):
    if value.lower() in settings.DISALLOWED_CHALLENGE_NAMES:
        raise ValidationError("That name is not allowed.")


def get_logo_path(instance, filename):
    return (
        f"logos/{instance.__class__.__name__.lower()}/{instance.pk}/{filename}"
    )


def get_banner_path(instance, filename):
    return f"banners/{instance.pk}/{filename}"


class TaskType(models.Model):
    """
    Stores the task type options, eg, Segmentation, Regression, Prediction, etc
    """

    type = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("type",)

    def __str__(self):
        return self.type

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.type)
        return f"task-{cls}"


class ImagingModality(models.Model):
    """ Stores the modality options, eg, MR, CT, PET, XR """

    modality = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("modality",)

    def __str__(self):
        return self.modality

    @property
    def filter_tag(self):
        cls = re.sub(r"\W+", "", self.modality)
        return f"modality-{cls}"


class BodyRegion(models.Model):
    """ Stores the anatomy options, eg, Head, Neck, Thorax, etc """

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
    """ Stores the organ name and what region it belongs to """

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
    logo = models.ImageField(upload_to=get_logo_path, blank=True)
    hidden = models.BooleanField(
        default=True,
        help_text="Do not display this Project in any public overview",
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

    number_of_training_cases = models.IntegerField(blank=True, null=True)
    number_of_test_cases = models.IntegerField(blank=True, null=True)
    filter_classes = ArrayField(
        CICharField(max_length=32), default=list, editable=False
    )

    objects = ChallengeManager()

    def __str__(self):
        """ string representation for this object"""
        return self.short_name

    @property
    def thumb_image_url(self):
        try:
            return self.logo.url
        except ValueError:
            return (
                f"https://www.gravatar.com/avatar/"
                f"{hashlib.md5(self.creator.email.lower().encode()).hexdigest()}"
            )

    def get_absolute_url(self):
        raise NotImplementedError

    @property
    def hosted_on_comic(self):
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

        classes.add(self.get_host_id())

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

        return list(classes)

    def get_host_id(self):
        """
        Copied from grandchallenge_tags

        Try to find out what framework this challenge is hosted on, return
        a string which can also be an id or class in HTML
        """
        if self.hosted_on_comic:
            return "grand-challenge"

        if "codalab.org" in self.get_absolute_url():
            return "codalab"

        else:
            return "Unknown"

    def get_host_link(self):
        """
        Copied from grandchallenge tags

        Try to find out what framework this challenge is hosted on
        """
        host_id = self.get_host_id()

        if host_id == "grand-challenge":
            framework_name = "grand-challenge.org"
            framework_url = "http://grand-challenge.org"
        elif host_id == "codalab":
            framework_name = "codalab.org"
            framework_url = "http://codalab.org"
        else:
            return None

        return f"<a href={framework_url}>{framework_name}</a>"

    class Meta:
        abstract = True


class Challenge(ChallengeBase):
    """
    A collection of HTML pages using a certain skin. Pages can be browsed and
    edited.
    """

    public_folder = "public_html"
    skin = models.CharField(
        max_length=225,
        default=public_folder + "/project.css",
        help_text="css file to include throughout this"
        " project. relative to project data folder",
    )
    banner = models.ImageField(upload_to=get_banner_path, blank=True)
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

    # TODO check whether short name is really clean and short!
    def delete(self, using=None, keep_parents=False):
        """ Ensure that there are no orphans """
        self.admins_group.delete(using)
        self.participants_group.delete(using)
        super().delete(using, keep_parents)

    def get_project_data_folder(self):
        """ Full path to root folder for all data belonging to this project
        """
        return safe_join(settings.MEDIA_ROOT, self.short_name)

    def upload_dir_rel(self):
        """Path to get and put secure uploaded files relative to MEDIA_ROOT

        """
        return os.path.join(self.short_name, "uploads")

    def public_upload_dir_rel(self):
        """ Path to public uploaded files, relative to MEDIA_ROOT

        """
        return os.path.join(self.short_name, settings.COMIC_PUBLIC_FOLDER_NAME)

    def admin_group_name(self):
        """
        returns the name of the admin group which should have all rights to
        this ComicSite instance
        """
        return self.short_name + "_admins"

    def participants_group_name(self):
        """
        returns the name of the participants group, which should have some
        rights to this ComicSite instance
        """
        return self.short_name + "_participants"

    def is_admin(self, user) -> bool:
        """
        is user in the admins group for the comicsite to which this object
        belongs? superuser always passes
        """
        return (
            user.is_superuser
            or user.groups.filter(pk=self.admins_group.pk).exists()
        )

    def is_participant(self, user) -> bool:
        """
        is user in the participants group for the comicsite to which this
        object belong? superuser always passes
        """
        return (
            user.is_superuser
            or user.groups.filter(pk=self.participants_group.pk).exists()
        )

    def get_admins(self):
        """ Return all users that are in this comicsites admin group """
        return self.admins_group.user_set.all()

    def get_participants(self):
        """ Return all participants of this challenge """
        return self.participants_group.user_set.all()

    def get_absolute_url(self):
        """ With this method, admin will show a 'view on site' button """
        return reverse("challenge-homepage", args=[self.short_name])

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
    def hosted_on_comic(self):
        return False


class ComicSiteModel(models.Model):
    """
    An object which can be shown or used in the comicsite framework.
    This base class should handle common functions such as authorization.
    """

    title = models.SlugField(max_length=64, blank=False)
    challenge = models.ForeignKey(
        Challenge,
        help_text="To which comicsite does this object belong?",
        on_delete=models.CASCADE,
    )
    ALL = "ALL"
    REGISTERED_ONLY = "REG"
    ADMIN_ONLY = "ADM"
    STAFF_ONLY = "STF"
    PERMISSIONS_CHOICES = (
        (ALL, "All"),
        (REGISTERED_ONLY, "Registered users only"),
        (ADMIN_ONLY, "Administrators only"),
    )
    PERMISSION_WEIGHTS = ((ALL, 0), (REGISTERED_ONLY, 1), (ADMIN_ONLY, 2))
    permission_lvl = models.CharField(
        max_length=3, choices=PERMISSIONS_CHOICES, default=ALL
    )

    def __str__(self):
        """ string representation for this object"""
        return self.title

    def can_be_viewed_by(self, user):
        """ boolean, is user allowed to view this? """
        if self.permission_lvl == self.ALL:
            return True
        else:
            return user.has_perm("view_ComicSiteModel", self)

    def setpermissions(self, lvl):
        """ Give the right groups permissions to this object
            object needs to be saved before setting perms"""
        admingroup = self.challenge.admins_group
        participantsgroup = self.challenge.participants_group
        self.persist_if_needed()
        if lvl == self.ALL:
            assign_perm("view_ComicSiteModel", admingroup, self)
            assign_perm("view_ComicSiteModel", participantsgroup, self)
        elif lvl == self.REGISTERED_ONLY:
            assign_perm("view_ComicSiteModel", admingroup, self)
            assign_perm("view_ComicSiteModel", participantsgroup, self)
        elif lvl == self.ADMIN_ONLY:
            assign_perm("view_ComicSiteModel", admingroup, self)
            remove_perm("view_ComicSiteModel", participantsgroup, self)
        else:
            raise ValueError(
                f"Unknown permissions level '{lvl}'. "
                "I don't know which groups to give permissions to this object"
            )

    def persist_if_needed(self):
        """
        setting permissions needs a persisted object. This method makes sure.
        """
        if not self.id:
            super().save()

    def save(self, *args, **kwargs):
        self.setpermissions(self.permission_lvl)
        super().save()

    class Meta:
        abstract = True
        permissions = (("view_ComicSiteModel", "Can view Comic Site Model"),)
