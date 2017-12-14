import copy
import datetime
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.storage import DefaultStorage
from django.core.validators import validate_slug, MinLengthValidator
from django.db import models
from django.db.models import Max
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from guardian.shortcuts import assign_perm, remove_perm

import comicsite.utils.query
from ckeditor.fields import RichTextField
from comicmodels.template.decorators import track_data
from comicsite.core.urlresolvers import reverse

logger = logging.getLogger("django")


def giveFileUploadDestinationPath(uploadmodel, filename):
    """ Where should this file go relative to MEDIA_ROOT?
    Determines location based on permission level of the uploaded model.

    """

    # uploadmodel can be either a ComicSite, meaning a
    # header image or something belonging to a ComicSite is being uploaded, or
    # a ComicSiteModel, meaning it is some inheriting class
    # TODO: This is confused code. Have a single way of handling uploads,
    # lika a small js browser with upload capability.


    if hasattr(uploadmodel, 'short_name'):
        is_comicsite = True
    else:
        is_comicsite = False

    if is_comicsite:
        comicsite = uploadmodel
        # Any image uploaded as part of a comcisite is public. These images
        # are only headers and other public things
        permission_lvl = ComicSiteModel.ALL
    else:
        comicsite = uploadmodel.comicsite
        permission_lvl = uploadmodel.permission_lvl

    # If permission is ALL, upload this file to the public_html folder
    if permission_lvl == ComicSiteModel.ALL:
        """Since we want this procedure only working for a specific Challenge (i.e., LUNA16) we put this flag. Hardcoding name of specific Challenge LUNA16"""

        if str(uploadmodel.comicsite) == "LUNA16":
            path = os.path.join(comicsite.public_upload_dir_rel(),
                                os.path.join('%s' % uploadmodel.user,
                                             '%s_' % (
                                                 datetime.datetime.now().strftime(
                                                     '%Y%m%d_%H%M%S')) + filename))

        else:
            path = os.path.join(comicsite.public_upload_dir_rel(), filename)
    else:

        if str(uploadmodel.comicsite) == "LUNA16":
            path = os.path.join(comicsite.upload_dir_rel(),
                                os.path.join('%s' % uploadmodel.user,
                                             '%s_' % (
                                                 datetime.datetime.now().strftime(
                                                     '%Y%m%d_%H%M%S')) + filename))

        else:
            path = os.path.join(comicsite.upload_dir_rel(), filename)

    path = path.replace("\\",
                        "/")  # replace remove double slashes because this can mess up django's url system
    return path


def get_anonymous_user():
    """Anymous user is the default user for non logged in users. I is also the only member of group
      'everyone' for which permissions can be set """
    User = get_user_model()
    return User.objects.get(username=settings.ANONYMOUS_USER_NAME)


def get_project_admin_instance_name(projectname):
    """ Convention for naming the projectadmin interface for the given project
    Defining this here so it can be used from anywhere without needing a 
    ComicSite Instance.
    """

    return "{}admin".format(projectname.lower())


def get_projectname(project_admin_instance_name):
    """ Return lowercase projectname for an admin instance admin instance name.
    For example for 'caddementiaadmin' return project name 'caddementia'
    
    In some places, for example middleware/project.py, the project_admin_instance_name
    is the only lead we have for determining which project the request is associated with.
    In those place you want to get the project name back from the admin_instance_name
    
    """
    if not "admin" in project_admin_instance_name:
        raise ValueError(
            "expected an admin site instance name ending in 'admin',"
            " but did not find this in value '{}'".format(
                project_admin_instance_name))
    return project_admin_instance_name[:-5]


class ComicSiteManager(models.Manager):
    """ adds some tabel level functions for getting ComicSites from db. """

    def non_hidden(self):
        """ like all(), but only return ComicSites for which hidden=false"""
        return self.filter(hidden=False)

    def get_queryset(self):
        return super(ComicSiteManager, self).get_queryset()


class ProjectLink(object):
    """ Metadata about a single project: url, event etc. Used as the shared class
    for both external challenges and projects hosted on comic so they can be
    shown on the projectlinks overview page

    """

    # Using dict instead of giving a lot of fields to this object because the former
    # is easier to work with
    defaults = {"abreviation": "",
                "title": "",
                "description": "",
                "URL": "",
                "submission URL": "",
                "event name": "",
                "year": "",
                "event URL": "",
                "image URL": "",
                "website section": "",
                "overview article url": "",
                "overview article journal": "",
                "overview article citations": "",
                "overview article date": "",
                "submission deadline": "",
                "workshop date": "",
                "open for submission": "",
                "dataset downloads": "",
                "registered teams": "",
                "submitted results": "",
                "last submission date": "",
                "hosted on comic": False,
                "project type": ""
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
            # this happens when excel says its a number. I dont want to force the
            # excel file to be clean, so deal with it here.
            if type(datestr) == float:
                datestr = str(datestr)[0:8]

            try:
                date = timezone.make_aware(
                    datetime.datetime.strptime(datestr, "%Y%m%d"),
                    timezone.get_default_timezone())
            except ValueError as e:
                logger.warning(
                    "could not parse date '%s' from xls line starting with '%s'. Returning default date 2013-01-01" % (
                        datestr, self.params["abreviation"]))
                date = ""

        if date == "":
            # If you cannot find the exact date for a project,
            # use date created
            if self.params["hosted on comic"]:
                return self.params["created at"]
            # If you cannot find the exact date, try to get at least the year right.
            # again do not throw errors, excel can be dirty

            year = int(self.params["year"])

            try:
                date = timezone.make_aware(datetime.datetime(year, 1, 1),
                                           timezone.get_default_timezone())
            except ValueError:
                logger.warning(
                    "could not parse year '%f' from xls line starting with '%s'. Returning default date 2013-01-01" % (
                        year, self.params["abreviation"]))
                date = timezone.make_aware(datetime.datetime(2013, 1, 1),
                                           timezone.get_default_timezone())

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

        linkclass = ComicSite.CHALLENGE_ACTIVE

        # for project hosted on comic, try to find upcoming/active automatically

        if self.params["hosted on comic"]:
            linkclass = self.params["project type"]

            if self.date > self.to_datetime(datetime.datetime.today()):
                linkclass += " " + self.UPCOMING

        else:
            # else use the explicit setting in xls

            section = self.params["website section"].lower()
            if section == "upcoming challenges":
                linkclass = ComicSite.CHALLENGE_ACTIVE + " " + self.UPCOMING
            elif section == "active challenges":
                linkclass = ComicSite.CHALLENGE_ACTIVE
            elif section == "past challenges":
                linkclass = ComicSite.CHALLENGE_INACTIVE
            elif section == "data publication":
                linkclass = ComicSite.DATA_PUB

        return linkclass

    def to_datetime(self, date):
        """ add midnight to a date to make it a datetime because I cannot
        ompare these two types directly. Also add offset awareness to easily
        compare with other django datetimes.
        """

        dt = datetime.datetime(date.year, date.month, date.day)
        return timezone.make_aware(dt, timezone.get_default_timezone())

    def is_hosted_on_comic(self):
        return self.params["hosted on comic"]


def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError(u"underscores not allowed. The url \
            '{0}.{1}' would not be valid, please use hyphens (-).".format(
            value, settings.MAIN_PROJECT_NAME))


class ComicSite(models.Model):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""

    public_folder = "public_html"

    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                null=True,
                                on_delete=models.SET_NULL)

    short_name = models.SlugField(max_length=50, default="",
                                  help_text="short name used in url, specific css, files etc. No spaces allowed",
                                  validators=[validate_nounderscores,
                                              validate_slug,
                                              MinLengthValidator(1)],
                                  unique=True)
    skin = models.CharField(max_length=225,
                            default=public_folder + "/project.css",
                            help_text="css file to include throughout this"
                                      " project. relative to project data folder")
    description = models.CharField(max_length=1024, default="",
                                   blank=True, help_text="Short summary of "
                                                         "this project, max 1024 characters.")
    logo = models.CharField(max_length=255,
                            default=public_folder + "/logo.png",
                            help_text="100x100 pixel image file to use as logo"
                                      " in projects overview. Relative to project datafolder")
    header_image = models.CharField(max_length=255, blank=True,
                                    help_text="optional 658 pixel wide Header image which will "
                                              "appear on top of each project page top of each "
                                              "project. "
                                              "Relative to project datafolder. Suggested default:" + public_folder + "/header.png")

    hidden = models.BooleanField(default=True,
                                 help_text="Do not display this Project in any public overview")
    hide_signin = models.BooleanField(default=False,
                                      help_text="Do no show the Sign in / Register link on any page")
    hide_footer = models.BooleanField(default=False,
                                      help_text="Do not show the general links or the grey divider line in page footers")

    disclaimer = models.CharField(max_length=2048, default="", blank=True,
                                  null=True,
                                  help_text="Optional text to show on each page in the project. For showing 'under construction' type messages")

    created_at = models.DateTimeField(auto_now_add=True)

    workshop_date = models.DateField(null=True, blank=True,
                                     help_text="Date on which the workshop belonging to this project will be held")
    event_name = models.CharField(max_length=1024, default="", blank=True,
                                  null=True,
                                  help_text="The name of the event the workshop will be held at")
    event_url = models.URLField(blank=True, null=True,
                                help_text="Website of the event which will host the workshop")

    CHALLENGE_ACTIVE = 'challenge_active'
    CHALLENGE_INACTIVE = 'challenge_inactive'
    DATA_PUB = 'data_pub'

    is_open_for_submissions = models.BooleanField(default=False,
                                                  help_text="This project currently accepts new submissions. Affects listing in projects overview")
    submission_page_name = models.CharField(blank=True, null=True,
                                            max_length=255,
                                            help_text="If the project allows submissions, there will be a link in projects overview going directly to you project/<submission_page_name>/. If empty, the projects main page will be used instead")
    number_of_submissions = models.IntegerField(blank=True, null=True,
                                                help_text="The number of submissions have been evalutated for this project")
    last_submission_date = models.DateField(null=True, blank=True,
                                            help_text="When was the last submission evaluated?")

    offers_data_download = models.BooleanField(default=False,
                                               help_text="This project currently accepts new submissions. Affects listing in projects overview")
    number_of_downloads = models.IntegerField(blank=True, null=True,
                                              help_text="How often has the dataset for this project been downloaded?")

    publication_url = models.URLField(blank=True, null=True,
                                      help_text="URL of a publication describing this project")
    publication_journal_name = models.CharField(max_length=225, blank=True,
                                                null=True,
                                                help_text="If publication was in a journal, please list the journal name here"
                                                          " We use <a target='new' href='https://www.ncbi.nlm.nih.gov/nlmcatalog/journals'>PubMed journal abbreviations</a> format")
    require_participant_review = models.BooleanField(default=False,
                                                     help_text="If ticked, new participants need to be approved by project admins before they can access restricted pages. If not ticked, new users are allowed access immediately")

    use_evaluation = models.BooleanField(default=False,
                                         help_text="If true, use the automated evaluation system. See the evaluation page created in the Challenge site.")

    admins_group = models.OneToOneField(
        Group,
        null=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name='admins_of_challenge'
    )

    participants_group = models.OneToOneField(
        Group,
        null=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name='participants_of_challenge'
    )

    objects = ComicSiteManager()

    def __str__(self):
        """ string representation for this object"""
        return self.short_name

    def clean(self):
        """ clean method is called automatically for each save in admin"""
        pass
        # TODO check whether short name is really clean and short!

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
        return os.path.join(settings.MEDIA_ROOT,
                            self.public_upload_dir_rel())

    def public_upload_dir_rel(self):
        """ Path to public uploaded files, relative to MEDIA_ROOT

        """
        return os.path.join(self.short_name, settings.COMIC_PUBLIC_FOLDER_NAME)

    def get_project_admin_instance_name(self):
        """ Each comicsite has a dedicated django admin instance. Return the
        name for this instance. This can be used in reverse() like this:
        
        # will return url to root admin instance (shows all projects/objects)
        reverse("admin:index") 
        
        # will return url to admin specific to this project (shows only objects 
        # for this project)
        reverse("admin:index", name = self.get_project_admin_instance_name())
        """

        return get_project_admin_instance_name(self.short_name)

    def admin_group_name(self):
        """ returns the name of the admin group which should have all rights to this ComicSite instance"""
        return self.short_name + "_admins"

    def participants_group_name(self):
        """ returns the name of the participants group, which should have some rights to this ComicSite instance"""
        return self.short_name + "_participants"

    def get_relevant_perm_groups(self):
        """ Return all auth groups which are directly relevant for this ComicSite.
            This method is used for showin permissions for these groups, even if none
            are defined """

        groups = Group.objects.filter(
            Q(name=settings.EVERYONE_GROUP_NAME) | Q(
                name=self.admin_group_name()) | Q(
                name=self.participants_group_name()))
        return groups

    def is_admin(self, user):
        """ is user in the admins group for the comicsite to which this object belongs? superuser always passes

        """
        if user.is_superuser:
            return True

        if user.groups.filter(name=self.admin_group_name()).exists():
            return True
        else:
            return False

    def is_participant(self, user):
        """ is user in the participants group for the comicsite to which this object belong? superuser always passes

        """
        if user.is_superuser:
            return True

        if user.groups.filter(name=self.participants_group_name()).exists():
            return True
        else:
            return False

    def get_admins(self):
        """ Return array of all users that are in this comicsites admin group, including superusers
        """
        User = get_user_model()
        admins = User.objects.filter(
            Q(groups__name=self.admin_group_name()) | Q(
                is_superuser=True)).distinct()
        return admins

    def get_absolute_url(self):
        """ With this method, admin will show a 'view on site' button """

        url = reverse('comicsite.views.site', args=[self.short_name])
        return url

    def to_projectlink(self):
        """ Return a ProjectLink representation of this comicsite, to show in an
        overview page listing all projects

        """

        thumb_image_url = reverse('project_serve_file',
                                  args=[self.short_name, self.logo])

        args = {"abreviation": self.short_name,
                "title": self.short_name,
                "description": self.description,
                "URL": reverse('comicsite.views.site', args=[self.short_name]),
                "download URL": "",
                "submission URL": self.get_submission_URL(),
                "event name": self.event_name,
                "year": "",
                "event URL": self.event_url,
                "image URL": self.logo,
                "thumb_image_url": thumb_image_url,
                "website section": "active challenges",
                "overview article url": self.publication_url,
                "overview article journal": self.publication_journal_name,
                "overview article citations": "",
                "overview article date": "",
                "submission deadline": "",
                "workshop date": self.workshop_date,
                "open for submission": "yes" if self.is_open_for_submissions else "no",
                "data download": "yes" if self.offers_data_download else "no",
                "dataset downloads": self.number_of_downloads,
                "registered teams": "",
                "submitted results": self.number_of_submissions,
                "last submission date": self.last_submission_date,
                "hosted on comic": True,
                "created at": self.created_at
                }

        projectlink = ProjectLink(args)
        return projectlink

    def get_submission_URL(self):
        """ What url can you go to to submit for this project? """
        URL = reverse('comicsite.views.site', args=[self.short_name])
        if self.submission_page_name:
            if self.submission_page_name.startswith(
                    "http://") or self.submission_page_name.startswith(
                "https://"):
                # the url in the submission page box is a full url
                return self.submission_page_name
            else:
                page = self.submission_page_name
                if not page.endswith("/"):
                    page += "/"
                URL += page
        return URL

    def add_participant(self, user):
        group = Group.objects.get(name=self.participants_group_name())
        user.groups.add(group)

    def remove_participant(self, user):
        group = Group.objects.get(name=self.participants_group_name())
        user.groups.remove(group)

    def add_admin(self, user):
        group = Group.objects.get(name=self.admin_group_name())
        user.groups.add(group)

    def remove_admin(self, user):
        group = Group.objects.get(name=self.admin_group_name())
        user.groups.remove(group)

    class Meta:
        verbose_name = "challenge"
        verbose_name_plural = "challenges"


class ComicSiteModel(models.Model):
    """An object which can be shown or used in the comicsite framework. This base class should handle common functions
     such as authorization.
    """
    title = models.SlugField(max_length=64, blank=False)
    comicsite = models.ForeignKey(ComicSite,
                                  help_text="To which comicsite does this object belong?")

    ALL = 'ALL'
    REGISTERED_ONLY = 'REG'
    ADMIN_ONLY = 'ADM'

    PERMISSIONS_CHOICES = (
        (ALL, 'All'),
        (REGISTERED_ONLY, 'Registered users only'),
        (ADMIN_ONLY, 'Administrators only')
    )

    PERMISSION_WEIGHTS = (
        (ALL, 0),
        (REGISTERED_ONLY, 1),
        (ADMIN_ONLY, 2)
    )

    permission_lvl = models.CharField(max_length=3,
                                      choices=PERMISSIONS_CHOICES,
                                      default=ALL)

    def __str__(self):
        """ string representation for this object"""
        return self.title

    def can_be_viewed_by(self, user):
        """ boolean, is user allowed to view this? """

        # check whether everyone is allowed to view this. Anymous user is the only member of group
        # 'everyone' for which permissions can be set
        anonymousUser = get_anonymous_user()

        if anonymousUser.has_perm("view_ComicSiteModel", self):
            return True
        else:
            # if not everyone has access, check whether given user has permissions
            return user.has_perm("view_ComicSiteModel", self)

    def setpermissions(self, lvl):
        """ Give the right groups permissions to this object
            object needs to be saved before setting perms"""

        admingroup = Group.objects.get(name=self.comicsite.admin_group_name())
        participantsgroup = Group.objects.get(
            name=self.comicsite.participants_group_name())
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
                "Unknown permissions level '" + lvl + "'. I don't know which groups to give permissions to this object")

    def persist_if_needed(self):
        """ setting permissions needs a persisted object. This method makes sure."""
        if not self.id:
            super(ComicSiteModel, self).save()

    def save(self, *args, **kwargs):
        self.setpermissions(self.permission_lvl)
        super(ComicSiteModel, self).save()

    class Meta:
        abstract = True
        permissions = (("view_ComicSiteModel", "Can view Comic Site Model"),)


class Page(ComicSiteModel):
    """ A single editable page containing html and maybe special output plugins """

    order = models.IntegerField(editable=False, default=1,
                                help_text="Determines order in which page appear in site menu")
    display_title = models.CharField(max_length=255, default="", blank=True,
                                     help_text="On pages and in menu items, use this text. Spaces and special chars allowed here. Optional field. If emtpy, title is used")
    hidden = models.BooleanField(default=False,
                                 help_text="Do not display this page in site menu")
    html = RichTextField()

    def clean(self):
        """ clean method is called automatically for each save in admin"""

        # when saving for the first time only, put this page last in order
        if not self.id:
            # get max value of order for current pages.
            try:
                max_order = Page.objects.filter(
                    comicsite__pk=self.comicsite.pk).aggregate(Max('order'))
            except ObjectDoesNotExist:
                max_order = None

            if max_order["order__max"] is None:
                self.order = 1
            else:
                self.order = max_order["order__max"] + 1

    def rawHTML(self):
        """Display html of this page as html. This uses the mark_safe django method to allow direct html rendering"""
        # TODO : do checking for scripts and hacks here?
        return mark_safe(self.html)

    def rawHTMLrendered(self):
        """Display raw html, but render any template tags found using django's template system """

    def move(self, move):
        if move == 'UP':
            mm = Page.objects.get(comicsite=self.comicsite,
                                  order=self.order - 1)
            mm.order += 1
            mm.save()
            self.order -= 1
            self.save()
        if move == 'DOWN':
            mm = Page.objects.get(comicsite=self.comicsite,
                                  order=self.order + 1)
            mm.order -= 1
            mm.save()
            self.order += 1
            self.save()
        if move == 'FIRST':
            pages = Page.objects.filter(comicsite=self.comicsite)
            idx = comicsite.utils.query.index(pages, self)
            pages[idx].order = pages[0].order - 1
            pages = sorted(pages, key=lambda page: page.order)
            self.normalize_page_order(pages)
        if move == 'LAST':
            pages = Page.objects.filter(comicsite=self.comicsite)
            idx = comicsite.utils.query.index(pages, self)
            pages[idx].order = pages[len(pages) - 1].order + 1
            pages = sorted(pages, key=lambda page: page.order)
            self.normalize_page_order(pages)

    def normalize_page_order(self, pages):
        """Make sure order in pages Queryset starts at 1 and increments 1 at
        every page. Saves all pages
         
        """
        for index, page in enumerate(pages):
            page.order = index + 1
            page.save()

    def get_absolute_url(self):
        """ With this method, admin will show a 'view on site' button """

        url = reverse('comicsite.views.page',
                      args=[self.comicsite.short_name, self.title])
        return url

    class Meta(ComicSiteModel.Meta):
        """special class holding meta info for this class"""
        # make sure a single site never has two pages with the same name because page names
        # are used as keys in urls
        unique_together = (("comicsite", "title"),)

        # when getting a list of these objects this ordering is used
        ordering = ['comicsite', 'order']


class ErrorPage(Page):
    """ Just the same as a Page, just that it does not display an edit button as admin"""
    is_error_page = True

    def can_be_viewed_by(self, user):
        """ overwrites Page class method. Errorpages can always be viewed"""
        return True

    class Meta:
        abstract = True  # error pages should only be generated on the fly currently.


class UploadModel(ComicSiteModel):
    file = models.FileField(max_length=255,
                            upload_to=giveFileUploadDestinationPath)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             help_text="which user uploaded this?")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    @property
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1]

    @property
    def localfileexists(self):
        storage = DefaultStorage()
        return storage.exists(self.file.path)

    def clean(self):
        # When no title is set, take the filename as title

        if self.title == "":

            if self.file.name:  # is a
                # autofill title with the name the file is going to have
                # Some confused code here to get the filename a file is going to get.
                # We should have a custom storage class For Uploadmodels. The storage
                # class should know to save objects to their respective project

                validFilePath = self.file.storage.get_available_name(
                    self.file.field.generate_filename(self, self.file.name))
                self.title = os.path.basename(validFilePath)
            else:

                raise ValidationError(
                    "No file given, I don't know what title to give this uploaded file.")

    class Meta(ComicSiteModel.Meta):
        verbose_name = "uploaded file"
        verbose_name_plural = "uploaded files"


class RegistrationRequestManager(models.Manager):
    """ adds some convenient queries to standard .objects()"""

    def get_pending_registration_requests(self, user, site):
        """ So people can be shown that they have already sent a request and to make
        sure they don't (or some bot doesnt) request a 1000 times

        Return: RegistrationRequest object if it already exists, empty list if it
        does not
        """

        return self.filter(project=site,
                           user=user,
                           status=RegistrationRequest.PENDING)

    def get_accepted_registration_requests(self, user, site):
        """ So people can be shown that they have already sent a request and to make
        sure they don't (or some bot doesnt) request a 1000 times

        Return: RegistrationRequest object if it already exists, empty list if it
        does not
        """
        return self.filter(project=site,
                           user=user,
                           status=RegistrationRequest.ACCEPTED)

    def get_queryset(self):
        return super(RegistrationRequestManager, self).get_queryset()


@track_data('status')
class RegistrationRequest(models.Model):
    """ When a user wants to join a project, admins have the option of reviewing
        each user before allowing or denying them. This class records the needed
        info for that.
    """
    objects = RegistrationRequestManager()

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             help_text="which user requested to participate?")
    project = models.ForeignKey(ComicSite,
                                help_text="To which project does the user want to register?")

    created = models.DateTimeField(auto_now_add=True)
    changed = models.DateTimeField(blank=True, null=True)

    PENDING = 'PEND'
    ACCEPTED = 'ACPT'
    REJECTED = 'RJCT'

    REGISTRATION_CHOICES = (
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected')
    )

    status = models.CharField(max_length=4,
                              choices=REGISTRATION_CHOICES,
                              default=PENDING)

    # question: where to send email to admin? probably not here?

    def __str__(self):
        """ describes this object in admin interface etc.
        """
        return "{1} registration request by user {0}".format(
            self.user.username,
            self.project.short_name)

    def status_to_string(self):
        status = "Your participation request for " + self.project.short_name + \
                 ", sent " + self.format_date(self.created)

        if self.status == self.PENDING:
            status += ", is awaiting review"
        elif self.status == self.ACCEPTED:
            status += ", was accepted at " + self.format_date(self.changed)
        elif self.status == self.REJECTED:
            status += ", was rejected at " + self.format_date(self.changed)

        return status

    def format_date(self, date):
        return date.strftime('%b %d, %Y at %H:%M')

    def user_real_name(self):
        return self.user.first_name + " " + self.user.last_name

    def user_email(self):
        return self.user.email

    def user_affiliation(self):
        profile = self.user.user_profile
        return profile.institution + " - " + profile.department
