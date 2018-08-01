import copy
import datetime
import hashlib
import logging
import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug, MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user

from grandchallenge.core.urlresolvers import reverse

logger = logging.getLogger("django")


class ChallengeManager(models.Manager):
    """ adds some tabel level functions for getting ComicSites from db. """

    def non_hidden(self):
        """ like all(), but only return ComicSites for which hidden=false"""
        return self.filter(hidden=False)


class ProjectLink(object):
    """ Metadata about a single project: url, event etc. Used as the shared
    class for both external challenges and projects hosted on comic so they can
    be shown on the projectlinks overview page

    """
    # Using dict instead of giving a lot of fields to this object because the
    # former is easier to work with
    defaults = {
        "abreviation": "",
        "title": "",
        "description": "",
        "URL": "",
        "submission URL": "",
        "event name": "",
        "year": "",
        "event URL": "",
        "website section": "",
        "overview article url": "",
        "overview article journal": "",
        "workshop date": "",
        "open for submission": "",
        "dataset downloads": "",
        "submitted results": "",
        "last submission date": "",
        "hosted on comic": False,
        "project type": "",
        "excel": True,
    }
    # css selector used to designate a project as still open
    UPCOMING = "challenge_upcoming"

    def __init__(self, params, date=""):
        self.params = copy.deepcopy(self.defaults)
        self.params.update(params)
        # add date in addition to datestring already in dict, to make sorting
        # easier.
        if date == "":
            self.date = self.determine_project_date()
        else:
            self.date = date
        self.params["year"] = self.date.year

    def determine_project_date(self):
        """ Try to find the date for this project. Return default
        date if nothing can be parsed.

        """
        if self.params["hosted on comic"]:
            if self.params["workshop date"]:
                date = self.to_datetime(self.params["workshop date"])
            else:
                date = ""
        else:
            datestr = self.params["workshop date"]
            # this happens when excel says its a number. I dont want to force
            # the excel file to be clean, so deal with it here.
            if type(datestr) == float:
                datestr = str(datestr)[0:8]
            try:
                date = timezone.make_aware(
                    datetime.datetime.strptime(datestr, "%Y%m%d"),
                    timezone.get_default_timezone(),
                )
            except ValueError:
                logger.warning(
                    "could not parse date '%s' from xls line starting with "
                    "'%s'. Returning default date 2013-01-01" %
                    (datestr, self.params["abreviation"])
                )
                date = ""
        if date == "":
            # If you cannot find the exact date for a project,
            # use date created
            if self.params["hosted on comic"]:
                return self.params["created at"]

            # If you cannot find the exact date, try to get at least the year
            # right. again do not throw errors, excel can be dirty
            year = int(self.params["year"])
            try:
                date = timezone.make_aware(
                    datetime.datetime(year, 1, 1),
                    timezone.get_default_timezone(),
                )
            except ValueError:
                logger.warning(
                    "could not parse year '%f' from xls line starting with "
                    "'%s'. Returning default date 2013-01-01" %
                    (year, self.params["abreviation"])
                )
                date = timezone.make_aware(
                    datetime.datetime(2013, 1, 1),
                    timezone.get_default_timezone(),
                )
        return date

    def find_link_class(self):
        """ Get css classes to give to this projectlink.
        For filtering and sorting project links, we discern upcoming, active
        and inactive projects. Determiniation of upcoming/active/inactive is
        described in column 'website section' in grand-challenges xls.
        For projects hosted on comic, determine this automatically based on
        associated workshop date. If a comicsite has an associated workshop
        which is in the future, make it upcoming, otherwise active

        """
        linkclass = Challenge.CHALLENGE_ACTIVE
        # for project hosted on comic, try to find upcoming automatically
        if self.params["hosted on comic"]:
            linkclass = self.params["project type"]
            if self.date > self.to_datetime(datetime.datetime.today()):
                linkclass += " " + self.UPCOMING
        else:
            # else use the explicit setting in xls
            section = self.params["website section"].lower()
            if section == "upcoming challenges":
                linkclass = Challenge.CHALLENGE_ACTIVE + " " + self.UPCOMING
            elif section == "active challenges":
                linkclass = Challenge.CHALLENGE_ACTIVE
            elif section == "past challenges":
                linkclass = Challenge.CHALLENGE_INACTIVE
            elif section == "data publication":
                linkclass = Challenge.DATA_PUB
        return linkclass

    @staticmethod
    def to_datetime(date):
        """ add midnight to a date to make it a datetime because I cannot
        compare these two types directly. Also add offset awareness to easily
        compare with other django datetimes.
        """
        dt = datetime.datetime(date.year, date.month, date.day)
        return timezone.make_aware(dt, timezone.get_default_timezone())

    def is_hosted_on_comic(self):
        return self.params["hosted on comic"]

    def is_defined_in_excel(self):
        return self.params["excel"]


def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError(
            u"underscores not allowed. The url \
            '{0}.{1}' would not be valid, "
            u"please use hyphens (-)".format(value, settings.MAIN_PROJECT_NAME)
        )


def get_logo_path(instance, filename):
    return f"logos/{instance.__class__.__name__.lower()}/{instance.pk}/{filename}"


def get_banner_path(instance, filename):
    return f"banners/{instance.pk}/{filename}"


class ChallengeBase(models.Model):
    CHALLENGE_ACTIVE = 'challenge_active'
    CHALLENGE_INACTIVE = 'challenge_inactive'
    DATA_PUB = 'data_pub'

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    short_name = models.SlugField(
        max_length=50,
        default="",
        help_text=(
            "short name used in url, specific css, files etc. "
            "No spaces allowed"
        ),
        validators=[
            validate_nounderscores, validate_slug, MinLengthValidator(1)
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
        default='',
        help_text=(
            'The name of the challenge that is displayed on the All Challenges'
            ' page. If this is blank the short name of the challenge will be '
            'used.'
        ),
    )
    logo = models.ImageField(
        upload_to=get_logo_path,
        blank=True,
    )
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
    is_open_for_submissions = models.BooleanField(
        default=False,
        help_text=(
            "This project currently accepts new submissions. "
            "Affects listing in projects overview"
        ),
    )
    number_of_submissions = models.IntegerField(
        blank=True,
        null=True,
        help_text=(
            "The number of submissions have been evalutated for this project"
        ),
    )
    last_submission_date = models.DateField(
        null=True,
        blank=True,
        help_text="When was the last submission evaluated?",
    )
    offers_data_download = models.BooleanField(
        default=False,
        help_text=(
            "This project currently accepts new submissions. Affects listing "
            "in projects overview"
        ),
    )
    number_of_downloads = models.IntegerField(
        blank=True,
        null=True,
        help_text=(
            "How often has the dataset for this project been downloaded?"
        ),
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

    @property
    def submission_url(self):
        raise NotImplementedError

    def get_absolute_url(self):
        raise NotImplementedError

    @property
    def projectlink_args(self):
        return {
            # These are copied from ProjectLink
            "abreviation": self.short_name,
            "title": self.title if self.title else self.short_name,
            "description": self.description,
            "URL": self.get_absolute_url(),
            "submission URL": self.submission_url,
            "event name": self.event_name,
            "year": "",
            "event URL": self.event_url,
            "website section": "active challenges",
            "overview article url": self.publication_url,
            "overview article journal": self.publication_journal_name,
            "workshop date": self.workshop_date,
            "open for submission": "yes" if self.is_open_for_submissions else "no",
            "dataset downloads": self.number_of_downloads,
            "submitted results": self.number_of_submissions,
            "last submission date": self.last_submission_date,
            "hosted on comic": True,
            "excel": False,

            # These are extra
            "download URL": "",
            "thumb_image_url": self.thumb_image_url,
            "data download": "yes" if self.offers_data_download else "no",
            "created at": self.created_at,
        }

    def to_projectlink(self):
        """
        Return a ProjectLink representation of this comicsite, to show in an
        overview page listing all projects
        """
        return ProjectLink(self.projectlink_args)

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
    banner = models.ImageField(
        upload_to=get_banner_path,
        blank=True,
    )
    logo_path = models.CharField(
        max_length=255,
        default=public_folder + "/logo.png",
        help_text="100x100 pixel image file to use as logo"
                  " in projects overview. Relative to project datafolder",
    )
    header_image = models.CharField(
        max_length=255,
        blank=True,
        help_text="optional 658 pixel wide Header image which will "
                  "appear on top of each project page top of each "
                  "project. "
                  "Relative to project datafolder. Suggested default:" +
                  public_folder +
                  "/header.png",
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
    allow_unfiltered_page_html = models.BooleanField(
        default=False,
        help_text=(
            'If true, the page HTML is NOT filtered, allowing the challenge '
            'administrator to have full control over the page contents when '
            'they edit it in ckeditor.'
        )
    )
    use_registration_page = models.BooleanField(
        default=True,
        help_text='If true, show a registration page on the challenge site.',
    )
    registration_page_text = models.TextField(
        default='',
        blank=True,
        help_text=(
            'The text to use on the registration page, you could include '
            'a data usage agreement here. You can use HTML markup here.'
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
        related_name='admins_of_challenge',
    )
    participants_group = models.OneToOneField(
        Group,
        null=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name='participants_of_challenge',
    )
    submission_page_name = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text=(
            "If the project allows submissions, there will be a link in "
            "projects overview going directly to you "
            "project/<submission_page_name>/. If empty, the projects main "
            "page will be used instead"
        ),
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
        return os.path.join(settings.MEDIA_ROOT, self.short_name)

    def upload_dir(self):
        """Full path to get and put secure uploaded files. Files here cannot be
        viewed directly by url
        """
        return os.path.join(settings.MEDIA_ROOT, self.upload_dir_rel())

    def upload_dir_rel(self):
        """Path to get and put secure uploaded files relative to MEDIA_ROOT

        """
        return os.path.join(self.short_name, "uploads")

    def public_upload_dir(self):
        """Full path to get and put uploaded files. These files can be served
        to anyone without checking

         """
        return os.path.join(settings.MEDIA_ROOT, self.public_upload_dir_rel())

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

    def get_relevant_perm_groups(self):
        """
        Return all auth groups which are directly relevant for this ComicSite.
        This method is used for showin permissions for these groups, even
        if none are defined
        """
        groups = Group.objects.filter(
            Q(name=settings.EVERYONE_GROUP_NAME) |
            Q(pk=self.admins_group.pk) |
            Q(pk=self.participants_group.pk)
        )
        return groups

    def is_admin(self, user):
        """
        is user in the admins group for the comicsite to which this object
        belongs? superuser always passes
        """
        if user.is_superuser:
            return True

        if user.groups.filter(pk=self.admins_group.pk).exists():
            return True

        else:
            return False

    def is_participant(self, user):
        """
        is user in the participants group for the comicsite to which this
        object belong? superuser always passes
        """
        if user.is_superuser:
            return True

        if user.groups.filter(pk=self.participants_group.pk).exists():
            return True

        else:
            return False

    def get_admins(self):
        """ Return all users that are in this comicsites admin group """
        return self.admins_group.user_set.all()

    def get_participants(self):
        """ Return all participants of this challenge """
        return self.participants_group.user_set.all()

    def get_absolute_url(self):
        """ With this method, admin will show a 'view on site' button """
        return reverse('challenge-homepage', args=[self.short_name])

    @property
    def thumb_image_url(self):
        """ Legacy method for challenges that still use logo_path """
        try:
            return self.logo.url
        except ValueError:
            return reverse(
                'project_serve_file', args=[self.short_name, self.logo_path]
            )

    @property
    def submission_url(self):
        """ What url can you go to to submit for this project? """
        url = reverse('challenge-homepage', args=[self.short_name])
        if self.submission_page_name:
            if self.submission_page_name.startswith(
                    "http://"
            ) or self.submission_page_name.startswith(
                "https://"
            ):
                # the url in the submission page box is a full url
                return self.submission_page_name

            else:
                page = self.submission_page_name
                if not page.endswith("/"):
                    page += "/"
                url += page
        return url

    def add_participant(self, user):
        if user != get_anonymous_user():
            user.groups.add(self.participants_group)
        else:
            raise ValueError('You cannot add the anonymous user to this group')

    def remove_participant(self, user):
        user.groups.remove(self.participants_group)

    def add_admin(self, user):
        if user != get_anonymous_user():
            user.groups.add(self.admins_group)
        else:
            raise ValueError('You cannot add the anonymous user to this group')

    def remove_admin(self, user):
        user.groups.remove(self.admins_group)

    class Meta:
        verbose_name = "challenge"
        verbose_name_plural = "challenges"


class ExternalChallenge(ChallengeBase):
    homepage = models.URLField(
        blank=False,
        help_text=("What is the homepage for this challenge?"),
    )
    submission_page = models.URLField(
        blank=True,
        help_text=("Where is the submissions page for this challenge?")
    )
    download_page = models.URLField(
        blank=True,
        help_text=("Where is the download page for this challenge?")
    )

    @property
    def projectlink_args(self):
        """
        Override the project link arguments to get around the nasty hacks
        made in the excel sheet
        """
        args = super().projectlink_args

        args["hosted on comic"] = False

        if not self.workshop_date:
            args["workshop date"] = str(self.created_at)
            args["year"] = self.created_at.year
        else:
            args["workshop date"] = str(self.workshop_date)
            args["year"] = self.workshop_date.year

        if self.download_page:
            args["download URL"] = self.download_page

        return args

    def get_absolute_url(self):
        return self.homepage

    @property
    def submission_url(self):
        return self.submission_page


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
    ALL = 'ALL'
    REGISTERED_ONLY = 'REG'
    ADMIN_ONLY = 'ADM'
    PERMISSIONS_CHOICES = (
        (ALL, 'All'),
        (REGISTERED_ONLY, 'Registered users only'),
        (ADMIN_ONLY, 'Administrators only'),
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
        # check whether everyone is allowed to view this. Anymous user is the
        # only member of group 'everyone' for which permissions can be set
        anonymous_user = get_anonymous_user()
        if anonymous_user.has_perm("view_ComicSiteModel", self):
            return True

        else:
            # if not everyone has access,
            # check whether given user has permissions
            return user.has_perm("view_ComicSiteModel", self)

    def setpermissions(self, lvl):
        """ Give the right groups permissions to this object
            object needs to be saved before setting perms"""
        admingroup = self.challenge.admins_group
        participantsgroup = self.challenge.participants_group
        everyonegroup = Group.objects.get(name=settings.EVERYONE_GROUP_NAME)
        self.persist_if_needed()
        if lvl == self.ALL:
            assign_perm("view_ComicSiteModel", admingroup, self)
            assign_perm("view_ComicSiteModel", participantsgroup, self)
            assign_perm("view_ComicSiteModel", everyonegroup, self)
        elif lvl == self.REGISTERED_ONLY:
            assign_perm("view_ComicSiteModel", admingroup, self)
            assign_perm("view_ComicSiteModel", participantsgroup, self)
            remove_perm("view_ComicSiteModel", everyonegroup, self)
        elif lvl == self.ADMIN_ONLY:
            assign_perm("view_ComicSiteModel", admingroup, self)
            remove_perm("view_ComicSiteModel", participantsgroup, self)
            remove_perm("view_ComicSiteModel", everyonegroup, self)
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
            super(ComicSiteModel, self).save()

    def save(self, *args, **kwargs):
        self.setpermissions(self.permission_lvl)
        super(ComicSiteModel, self).save()

    class Meta:
        abstract = True
        permissions = (("view_ComicSiteModel", "Can view Comic Site Model"),)
