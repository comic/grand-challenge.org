import os
import re
import datetime
import pdb
import logging
import copy

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group,User,Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.core.validators import validate_slug, MaxLengthValidator
#from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils import timezone

from ckeditor.fields import RichTextField
from dropbox import client, rest, session
from dropbox.rest import ErrorResponse
from guardian.shortcuts import assign,remove_perm

from dataproviders import FileSystemDataProvider,DropboxDataProvider
from comicmodels.template.decorators import track_data
from comicsite.core.urlresolvers import reverse

logger = logging.getLogger("django")

def giveFileUploadDestinationPath(uploadmodel,filename):
    """ Where should this file go relative to MEDIA_ROOT?
    Determines location based on permission level of the uploaded model. 
    
    """
        
    # uploadmodel can be either a ComicSite, meaning a 
    # header image or something belonging to a ComicSite is being uploaded, or
    # a ComicSiteModel, meaning it is some inheriting class 
    # TODO: This is confused code. Have a single way of handling uploads,
    # lika a small js browser with upload capability.
    
    
    if hasattr(uploadmodel,'short_name'):
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
        path = os.path.join(comicsite.public_upload_dir_rel(),
                            filename)
    else:
        path = os.path.join(comicsite.upload_dir_rel(),
                            filename)

    path = path.replace("\\","/") # replace remove double slashes because this can mess up django's url system
    return path


def get_anonymous_user():
    """Anymous user is the default user for non logged in users. I is also the only member of group
      'everyone' for which permissions can be set """
    return User.objects.get(username = "AnonymousUser")


class ComicSiteManager(models.Manager):
    """ adds some tabel level functions for getting ComicSites from db. """ 
    
    def non_hidden(self):
        """ like all(), but only return ComicSites for which hidden=false"""
        return self.filter(hidden=False)
    
    def get_query_set(self):
        
        return super(ComicSiteManager, self).get_query_set()


class ProjectLink(object):
    """ Metadata about a single project: url, event etc. Used as the shared class
    for both external challenges and projects hosted on comic so they can be 
    shown on the projectlinks overview page
    
    """
    
    # Using dict instead of giving a lot of fields to this object because the former
    # is easier to work with 
    defaults = {"abreviation":"",
                "title":"",
                "description":"",
                "URL":"",
                "submission URL":"",
                "event name":"",
                "year":"",
                "event URL":"",
                "image URL":"",
                "website section":"",
                "overview article url":"",
                "overview article journal":"",
                "overview article citations":"",
                "overview article date":"",
                "submission deadline":"",
                "workshop date":"",
                "open for submission":"",
                "dataset downloads":"",
                "registered teams":"",
                "submitted results":"",
                "last submission date":"",
                "hosted on comic":False,
                "project type":""
                }
    
    
    # css selector used to designate a project as still open 
    UPCOMING = "challenge_upcoming"

    def __init__(self,params,date=""):
        
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
                date = timezone.make_aware(datetime.datetime.strptime(datestr,"%Y%m%d"),
                                           timezone.get_default_timezone())
            except ValueError as e:            
                logger.warn("could not parse date '%s' from xls line starting with '%s'. Returning default date 2013-01-01" %(datestr,self.params["abreviation"]))
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
                date = timezone.make_aware(datetime.datetime(year,01,01),
                                           timezone.get_default_timezone())
            except ValueError:
                logger.warn("could not parse year '%f' from xls line starting with '%s'. Returning default date 2013-01-01" %(year,self.params["abreviation"]))
                date = timezone.make_aware(datetime.datetime(2013,01,01),
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
                linkclass += " "+ self.UPCOMING            
                
        else:
            # else use the explicit setting in xls            
            
            section = self.params["website section"].lower()
            if section == "upcoming challenges":
                linkclass = ComicSite.CHALLENGE_ACTIVE +" "+ self.UPCOMING
            elif section == "active challenges":
                linkclass = ComicSite.CHALLENGE_ACTIVE
            elif section == "past challenges":
                linkclass = ComicSite.CHALLENGE_INACTIVE
            elif section == "data publication":
                linkclass = ComicSite.DATA_PUB

        return linkclass
     
    def to_datetime(self,date):
        """ add midnight to a date to make it a datetime because I cannot
        ompare these two types directly. Also add offset awareness to easily
        compare with other django datetimes.                  
        """
        
        dt = datetime.datetime(date.year,date.month,date.day)
        return timezone.make_aware(dt, timezone.get_default_timezone())
        
    def is_hosted_on_comic(self):
        return self.params["hosted on comic"]    
    
    def get_thumb_image_url(self):
        if self.is_hosted_on_comic():
            thumb_image_url = ""
        else:
            thumb_image_url = "http://shared.runmc-radiology.nl/mediawiki/challenges/localImage.php?file="+projectlink.params["abreviation"]+".png"
        
        return thumb_image_url
        

def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError(u"underscores not allowed. The url \
            '{0}.{1}' would not be valid, please use hyphens (-).".format(value,settings.MAIN_PROJECT_NAME))

class ComicSite(models.Model):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    public_folder = "public_html"
    
    short_name = models.SlugField(max_length = 50, default="", 
                                  help_text = "short name used in url, specific"
                                  " css, files etc. No spaces allowed",
                                  validators=[validate_nounderscores,validate_slug])
    skin = models.CharField(max_length = 225, default= public_folder+"/project.css", 
                            help_text = "css file to include throughout this"
                            " project. relative to project data folder")    
    description = models.CharField(max_length = 1024, default="",
                                   blank=True,help_text = "Short summary of "
                                   "this project, max 1024 characters.")
    logo = models.CharField(max_length = 255, default = public_folder+"/logo.png",
                            help_text = "100x100 pixel image file to use as logo" 
                            " in projects overview. Relative to project datafolder")
    header_image = models.CharField(max_length = 255, blank = True,
                            help_text = "optional 658 pixel wide Header image which will "
                            "appear on top of each project page top of each "
                            "project. " 
                            "Relative to project datafolder. Suggested default:"+public_folder+"/header.png")
        
    
    hidden = models.BooleanField(default=True, help_text = "Do not display this Project in any public overview")
    hide_signin = models.BooleanField(default=False, help_text = "Do no show the Sign in / Register link on any page")
    hide_footer = models.BooleanField(default=False, help_text = "Do not show the general links or the grey divider line in page footers")
    
    disclaimer = models.CharField(max_length = 2048, default="", blank=True, null=True, help_text = "Optional text to show on each page in the project. For showing 'under construction' type messages")
    
    created_at = models.DateTimeField(auto_now_add = True, default=timezone.now) #django.utils.timezone.now
    
    workshop_date = models.DateField(null=True, blank=True, help_text = "Date on which the workshop belonging to this project will be held")
    event_name = models.CharField(max_length = 1024, default="", blank=True, null=True, help_text="The name of the event the workshop will be held at")
    event_url = models.URLField(blank=True, null=True, help_text = "Website of the event which will host the workshop")

    CHALLENGE_ACTIVE = 'challenge_active'
    CHALLENGE_INACTIVE = 'challenge_inactive'
    DATA_PUB = 'data_pub'
    
    is_open_for_submissions = models.BooleanField(default=False, help_text = "This project currently accepts new submissions. Affects listing in projects overview")
    submission_page_name = models.CharField(blank=True, null=True,max_length=255,help_text= "If the project allows submissions, there will be a link in projects overview going directly to you project/<submission_page_name>/. If empty, the projects main page will be used instead")
    number_of_submissions = models.IntegerField(blank=True, null=True, help_text="The number of submissions have been evalutated for this project")
    last_submission_date = models.DateField(null=True, blank=True, help_text = "When was the last submission evaluated?")
    
    offers_data_download = models.BooleanField(default=False, help_text = "This project currently accepts new submissions. Affects listing in projects overview")    
    number_of_downloads = models.IntegerField(blank=True, null=True, help_text="How often has the dataset for this project been downloaded?")
    
    publication_url = models.URLField(blank=True, null=True, help_text = "URL of a publication describing this project")
    publication_journal_name = models.CharField(max_length = 225, blank=True, null=True,
                                                help_text = "If publication was in a journal, please list the journal name here"
                                                            " We use <a target='new' href='https://www.ncbi.nlm.nih.gov/nlmcatalog/journals'>PubMed journal abbreviations</a> format" ) 
    require_participant_review = models.BooleanField(default=False, help_text = "If ticked, new participants need to be approved by project admins before they can access restricted pages. If not ticked, new users are allowed access immediately")
     
    
    
    objects = ComicSiteManager()
    
    def __unicode__(self):
        """ string representation for this object"""
        return self.short_name
       
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        pass
        #TODO check whether short name is really clean and short!        
    
    
    def get_project_data_folder(self):
        """ Full path to root folder for all data belonging to this project
        """        
        return os.path.join(settings.MEDIA_ROOT,self.short_name)
            
    def upload_dir(self):
        """Full path to get and put secure uploaded files. Files here cannot be
        viewed directly by url
        """
        return os.path.join(settings.MEDIA_ROOT,self.upload_dir_rel())
    
    def upload_dir_rel(self):
        """Path to get and put secure uploaded files relative to MEDIA_ROOT
        
        """
        return os.path.join(self.short_name,"uploads")
    
    def public_upload_dir(self):
        """Full path to get and put uploaded files. These files can be served 
        to anyone without checking
        
         """
        return os.path.join(settings.MEDIA_ROOT,                            
                            self.public_upload_dir_rel())
         
    def public_upload_dir_rel(self):
        """ Path to public uploaded files, relative to MEDIA_ROOT
         
        """
        return os.path.join(self.short_name,settings.COMIC_PUBLIC_FOLDER_NAME)
    
    def admin_group_name(self):
        """ returns the name of the admin group which should have all rights to this ComicSite instance"""
        return self.short_name+"_admins"
    
    def participants_group_name(self):
        """ returns the name of the participants group, which should have some rights to this ComicSite instance"""
        return self.short_name+"_participants"
    
    def get_relevant_perm_groups(self):
        """ Return all auth groups which are directly relevant for this ComicSite. 
            This method is used for showin permissions for these groups, even if none
            are defined """
                
        groups = Group.objects.filter(Q(name="everyone") | Q(name=self.admin_group_name()) | Q(name=self.participants_group_name()))
        return groups
  
    def is_admin(self,user):
        """ is user in the admins group for the comicsite to which this object belongs? superuser always passes        
        
        """
        if user.is_superuser:
            return True
        
        if user.groups.filter(name=self.admin_group_name).count() > 0:
            return True
        else:
            return False
        
    def is_participant(self,user):
        """ is user in the participants group for the comicsite to which this object belong? superuser always passes
        
        """
        if user.is_superuser:
            return True
            
        if user.groups.filter(name=self.participants_group_name).count() > 0:
            return True
        else:
            return False
    
    def get_admins(self):
        """ Return array of all users that are in this comicsites admin group, including superusers
        """
        admins = User.objects.filter(Q(groups__name=self.admin_group_name()) | Q(is_superuser=True)).distinct()
        return admins
        
    def to_projectlink(self):
        """ Return a ProjectLink representation of this comicsite, to show in an
        overview page listing all projects
        
        """        
        
        thumb_image_url = reverse('project_serve_file', args=[self.short_name,self.logo])
        
        args = {"abreviation":self.short_name,
                "title":self.short_name,
                "description":self.description,
                "URL":reverse('comicsite.views.site', args=[self.short_name]),
                "download URL":"",
                "submission URL":self.get_submission_URL(),
                "event name":self.event_name,
                "year":"",
                "event URL":self.event_url,                
                "image URL":self.logo,
                "thumb_image_url":thumb_image_url,
                "website section":"active challenges",
                "overview article url":self.publication_url,
                "overview article journal":self.publication_journal_name,
                "overview article citations":"",
                "overview article date":"",
                "submission deadline":"",
                "workshop date":self.workshop_date,
                "open for submission":"yes" if self.is_open_for_submissions else "no",
                "data download":"yes" if self.offers_data_download else "no",
                "dataset downloads":self.number_of_downloads,
                "registered teams":"",
                "submitted results":self.number_of_submissions,
                "last submission date":self.last_submission_date,
                "hosted on comic":True,
                "created at":self.created_at                
                }
        
        projectlink = ProjectLink(args)
        return projectlink
    
    def get_submission_URL(self):
        """ What url can you go to to submit for this project? """
        URL = reverse('comicsite.views.site', args=[self.short_name])        
        if self.submission_page_name:
            if self.submission_page_name.startswith("http://") or self.submission_page_name.startswith("https://"):
                # the url in the submission page box is a full url                 
                return self.submission_page_name
            else:
                page = self.submission_page_name
                if not page.endswith("/"):
                    page += "/"
                URL += page
        return URL
        
    def add_participant(self,user):
        group = Group.objects.get(name=self.participants_group_name())                    
        user.groups.add(group)
    
    def remove_participant(self,user):
        group = Group.objects.get(name=self.participants_group_name())                    
        user.groups.remove(group)
        
  
              

class ComicSiteModel(models.Model):
    """An object which can be shown or used in the comicsite framework. This base class should handle common functions
     such as authorization.
    """
    #user = models.ManyToManyField()    
    title = models.SlugField(max_length=64, blank=True)    
    comicsite = models.ForeignKey(ComicSite, help_text = "To which comicsite does this object belong?")
    
    ALL = 'ALL'
    REGISTERED_ONLY = 'REG'
    ADMIN_ONLY = 'ADM'
    
    PERMISSIONS_CHOICES = (
        (ALL, 'All'),
        (REGISTERED_ONLY, 'Registered users only'),
        (ADMIN_ONLY, 'Administrators only')        
    )
    
    PERMISSION_WEIGHTS = (
        (ALL,0),
        (REGISTERED_ONLY,1),
        (ADMIN_ONLY,2)
    )
    
    permission_lvl = models.CharField(max_length=3,
                                      choices=PERMISSIONS_CHOICES,
                                      default=ALL)
    
    # = models.CharField(max_length=64, blank=True)
        
    
    
    
    def __unicode__(self):
       """ string representation for this object"""
       return self.title
   
    def can_be_viewed_by(self,user):
        """ boolean, is user allowed to view this? """
        
        # check whether everyone is allowed to view this. Anymous user is the only member of group
        # 'everyone' for which permissions can be set
        anonymousUser = get_anonymous_user()
        
        if anonymousUser.has_perm("view_ComicSiteModel",self):
            return True
        else:
            # if not everyone has access, check whether given user has permissions
            return user.has_perm("view_ComicSiteModel",self)
        
    
    def setpermissions(self, lvl):
        """ Give the right groups permissions to this object 
            object needs to be saved before setting perms"""
        
        admingroup = Group.objects.get(name=self.comicsite.admin_group_name())
        participantsgroup = Group.objects.get(name=self.comicsite.participants_group_name())
        everyonegroup = Group.objects.get(name="everyone")
        
        
        
        self.persist_if_needed()
        if lvl == self.ALL:
            assign("view_ComicSiteModel",admingroup,self)
            assign("view_ComicSiteModel",participantsgroup,self)
            assign("view_ComicSiteModel",everyonegroup,self)                    
        elif lvl == self.REGISTERED_ONLY:
            
            assign("view_ComicSiteModel",admingroup,self)
            assign("view_ComicSiteModel",participantsgroup,self)
            remove_perm("view_ComicSiteModel",everyonegroup,self)                    
        elif lvl == self.ADMIN_ONLY:
            
            assign("view_ComicSiteModel",admingroup,self)
            remove_perm("view_ComicSiteModel",participantsgroup,self)
            remove_perm("view_ComicSiteModel",everyonegroup,self)                    
        else:
            raise ValueError("Unknown permissions level '"+ lvl +"'. I don't know which groups to give permissions to this object")
    

        
    def persist_if_needed(self):
        """ setting permissions needs a persisted object. This method makes sure."""
        if not self.id:
            super(ComicSiteModel,self).save()

    def save(self, *args, **kwargs):
        """ split save into common base part for all ComicSiteModels and default which can be overwritten """        
        
        if self.id:
            firstcreation = False
        else:
            firstcreation = True
            
        #common save functionality for all models
        self._save_base()                
        self.save_default(firstcreation)
        super(ComicSiteModel,self).save()
    
    
    def _save_base(self):
        """ common save functionality for all models """                
        #make sure this object gets the permissions set in the form            
        self.setpermissions(self.permission_lvl)        
        
        
    def save_default(self,firstcreation):
        """ overwrite this in child methods for custom save functionality 
            object is saved after this method so no explicit save needed"""                
        pass

            
    class Meta:
       abstract = True
       permissions = (("view_ComicSiteModel", "Can view Comic Site Model"),)

class ProjectMetaData(models.Model):
    """ Things like event this project is associated to, whether there is an overview article, etcetera.
    Currently this info also part of the ComicSite model, and can be read from xls. However we need a form
    so people can add their own links on the site.
    
    The Projectlink class itself acts as a base class for information from ComicSites, xls file.
    it uses a dict to hold all variables so cannot be used in django admin directly.
    """
    
    contact_name = models.CharField(max_length = 255, default="",help_text = "Who is the main contact person for this project?")
    contact_email = models.EmailField(help_text = "")
        
    title = models.CharField(max_length = 255, default="", help_text = "Project title, will be printed in bold in projects overview")
    URL = models.URLField(blank=False, null=False, help_text = "URL of the main page of the project")
    description = models.TextField(max_length = 350, default="", blank=True, help_text = "Max 350 characters. Will be used in projects overview",
                                   validators=[MaxLengthValidator(350)])
    
    event_name = models.CharField(max_length = 255, default="", blank=True, help_text = "Name of the event this project is associated with, if any")
    event_URL = models.URLField(blank=True, null=True, help_text = "URL of the event this project is associated to, if any")
    
    submission_deadline = models.DateField(null=True, blank=True,help_text = "Deadline for submitting results to this project")
    workshop_date = models.DateField(blank=True,null=True)
    
    open_for_submissions = models.BooleanField(default=False, help_text = "This project accepts and evaluates submissions")
    submission_URL = models.URLField(blank=True, null=True, help_text = "Direct URL to a page where you can submit results")
    
    offers_data_download = models.BooleanField(default=False, help_text = "Data can be downloaded from this project's website")
    download_URL = models.URLField(blank=True, null=True, help_text = "Direct URL to a page where this data can be downloaded")
    
    def __unicode__(self):
        """ describes this object in admin interface etc.
        """
        return "ProjectMetadata '{0}'. Contact: {1}".format(self.title,self.contact_email)


class Page(ComicSiteModel):
    """ A single editable page containing html and maybe special output plugins """
    
    order = models.IntegerField(editable=False, default=1, help_text = "Determines order in which page appear in site menu")        
    display_title = models.CharField(max_length = 255, default="", blank=True, help_text = "On pages and in menu items, use this text. Spaces and special chars allowed here. Optional field. If emtpy, title is used")
    hidden = models.BooleanField(default=False, help_text = "Do not display this page in site menu")
    html = RichTextField()
    
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        
        #when saving for the first time only, put this page last in order 
        if not self.id:
            # get max value of order for current pages.
            try:            
                max_order = Page.objects.filter(comicsite__pk=self.comicsite.pk).aggregate(Max('order'))                
            except ObjectDoesNotExist :
                max_order = None
                                        
            if max_order["order__max"] == None:
                self.order = 1
            else:
                self.order = max_order["order__max"] + 1
      
    
    
    def rawHTML(self):
        """Display html of this page as html. This uses the mark_safe django method to allow direct html rendering"""
        #TODO : do checking for scripts and hacks here? 
        return mark_safe(self.html)
    
    def rawHTMLrendered(self):
        """Display raw html, but render any template tags found using django's template system """
    
    def move(self, move):
        if move == 'UP':
            mm = Page.objects.get(comicsite=self.comicsite,order=self.order-1)
            mm.order += 1
            mm.save()
            self.order -= 1
            self.save()
        if move == 'DOWN':
            mm = Page.objects.get(comicsite=self.comicsite,order=self.order+1)
            mm.order -= 1
            mm.save()
            self.order += 1
            self.save()
        if move == 'FIRST':
            raise NotImplementedError("Somebody should implement this!")
        if move == 'LAST':
            raise NotImplementedError("Somebody should implement this!")

    
    class Meta(ComicSiteModel.Meta):
        """special class holding meta info for this class"""
        # make sure a single site never has two pages with the same name because page names
        # are used as keys in urls
        unique_together = (("comicsite", "title"),)
         
        # when getting a list of these objects this ordering is used
        ordering = ['comicsite','order']        


class ErrorPage(Page):
    """ Just the same as a Page, just that it does not display an edit button as admin"""
    is_error_page=True
    
    def can_be_viewed_by(self,user):
        """ overwrites Page class method. Errorpages can always be viewed"""
        return True
    
    class Meta:
       abstract = True  #error pages should only be generated on the fly currently. 
       


class UploadModel(ComicSiteModel):
        
    file = models.FileField(max_length=255,upload_to=giveFileUploadDestinationPath)
    user = models.ForeignKey(User, help_text = "which user uploaded this?")
    created = models.DateTimeField(auto_now_add=True,default=datetime.date.today) 
    modified = models.DateTimeField(auto_now=True,default=datetime.date.today)
    
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
                        
            if self.file.name: #is a                 
                # autofill title with the name the file is going to have
                # Some confused code here to get the filename a file is going to get.
                # We should have a custom storage class For Uploadmodels. The storage
                # class should know to save objects to their respective project 
                
                validFilePath = self.file.storage.get_available_name(self.file.field.generate_filename(self,self.file.name))                               
                self.title = os.path.basename(validFilePath)
            else:
                
                raise ValidationError("No file given, I don't know what title to give this uploaded file.")                
    
    class Meta(ComicSiteModel.Meta):
        verbose_name = "uploaded file"
        verbose_name_plural = "uploaded files"
        

    
class Dataset(ComicSiteModel):
    """
    Collection of files
    """    
    description = models.TextField()
    
    
       
    @property
    def cleantitle(self):
        return re.sub('[\[\]/{}., ]+', '',self.title)       
                
    class Meta(ComicSiteModel.Meta):
       abstract = True
         
    
class FileSystemDataset(Dataset):
    """
    A folder location on disk
    """
    folder = models.FilePathField()
    folder_prefix = "datasets/"  # default initial subfolder to save datasets in, can be overwritten later on     
        
    def get_all_files(self):
        """ return array of all files in this folder
        """        
        dp = FileSystemDataProvider.FileSystemDataProvider(self.folder)
        filenames = dp.getFileNames()
        htmlOut = "available files:"+", ".join(filenames)
        return htmlOut

    
    def save_default(self,firstcreation):
                
        if firstcreation:
            # initialize data dir 
            data_dir = self.get_default_data_dir()
            self.folder = data_dir            
        else:
            # take possibly edited value from form, keep self.folder.
            pass                                          
        self.ensure_dir(self.get_full_folder_path())        
                    
        
    def get_full_folder_path(self):
        """ Return full path of the folder in which this datasets files reside """
        data_dir_path = os.path.join(settings.MEDIA_ROOT,self.folder)
        return data_dir_path
    
    def get_default_data_dir(self):
        """ In which dir should this dataset be located by default? Return path relative to MEDIA_ROOT  
        """                        
        data_dir_path = os.path.join(self.comicsite.short_name,self.folder_prefix,self.cleantitle)
        return data_dir_path
        
    def get_template_tag(self):
        """ Return the django template tag that can be used in page text to render this dataset on the page"""
        return "{% dataset " + self.cleantitle + " %}"
        
    def ensure_dir(self,dir):
        if not os.path.exists(dir):
            os.makedirs(dir)
            os.chmod(dir,0775) #refs #142


class DropboxFolder(ComicSiteModel):
    """
    Information to link with a single dropbox folder 
    """        
    access_token_key = models.CharField(max_length = 255, default="", blank=True)
    access_token_secret = models.CharField(max_length = 255, default="", blank=True)    
    last_status_msg = models.CharField(max_length = 1023, default="", blank=True)
        
    # status of this object, used for communicating with admin, which buttons to show 
    # when etc.
    NOT_SAVED = 'NOSAVE'
    READY_FOR_AUTH = "RFA"
    CONNECTED = 'CONNECTED'
    ERROR = 'ERROR'    
        
    STATUS_OPTIONS = ((NOT_SAVED,'Please save and reload to continue connecting to dropbox'), 
                      (READY_FOR_AUTH, 'Ready for authorization'),
                      (CONNECTED, ''))
    
    
    @property
    def cleantitle(self):
        return re.sub('[\[\]/{}., ]+', '',self.title)
    
    
    def save_default(self,firstcreation):
        """ overwrites comicSiteModel.save_default
        """
    
    
    def get_dropbox_data_provider(self):
        """ Get a data provider for this Dropboxfolder object.
            Data providers allows basic file operations like read and write        
        """
                
        dropbox_dp = DropboxDataProvider.DropboxDataProvider(settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET,
                                        settings.DROPBOX_ACCESS_TYPE, self.access_token_key, self.access_token_secret,
                                        location='',)
        return dropbox_dp
        
    
    def get_dropbox_app_keys(self):
        """ Get dropbox keys unique to COMIC. Throws AttributError if not found
        """
        return (settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET,settings.DROPBOX_ACCESS_TYPE)
                
    
    def get_connection_status(self):
        """Check whether this dropboxfolder can be accessed
        """
        
        if not self.pk:
            status = self.NOT_SAVED
            msg = "<span class='errors'>No connection. Please save and reload to connect to dropbox </span>"
                       
        # if no access keys have been set validation still needs to occur 
        elif self.access_token_key == '' or self.access_token_secret == '':
            try:  #check whether keys for COMIC itself are present.
                self.get_dropbox_app_keys()
            except AttributeError as e:
                status = self.ERROR
                msg = "ERROR: A key required for this app to connect to dropbox could not be found in settings..\
                        Has this been forgotten?. Original error: "+ str(e)
            
            status = self.READY_FOR_AUTH
            msg = "Ready for authorization."
        
        else: #if access keys have been filled, Try to get dropbox info to test connection
            try:
                
                info = self.get_info()
                status = self.CONNECTED                
                msg = "Connected to dropbox '" + info["display_name"] + "', owned by '"+info["email"]+"'"
            except ErrorResponse as e:
                status = self.ERROR
                msg = str(e) 
        
        if self.pk:            
            DropboxFolder.objects.filter(pk=self.pk).update(last_status_msg=msg)
        
        return (status,msg)
    
    
    def get_info(self):    
        """ Get account info for the given DropboxFolder object Throws ErrorResponse if info cannot be got.
        """
             
        (app_key,app_secret,access_type) = self.get_dropbox_app_keys()             
        sess = session.DropboxSession(app_key, app_secret, access_type)
        sess.set_token(self.access_token_key,self.access_token_secret)

        db_client = client.DropboxClient(sess)            
        
        #can throw ErrorResponse
        info = db_client.account_info()
                    
        message = info
                        
        return message
    
    
    def reset_connection(self,callback_host = ""):
        """ Generate a new link to authorize access to given dropbox. Will invalidate the old connection.
            callback_url will be passed with dropbox auth link so after authorization you are redirected.
        """
        
        #request new session, request new auth key
        (app_key,app_secret,access_type) = self.get_dropbox_app_keys()
        sess = session.DropboxSession(app_key, app_secret, access_type)
        request_token = sess.obtain_request_token()
        
        #visit this url to validate 
        url = sess.build_authorize_url(request_token)
        
        finalize_url = reverse('django_dropbox.views.finalize_connection',kwargs={'dropbox_folder_id':self.id}) 
        
        if callback_host == "":
            msg = (request_token,"Please visit <a href=\""+url+"\" target=\"_new\"> this link</a>  to authorize access to dropbox.\
                                  After authorizing, click <a href=\""+finalize_url+"\">this link</a>")
        else:
            url = url + "&oauth_callback="+callback_host+finalize_url
            msg = (request_token,"Please visit <a href=\""+url+"\"> this link</a> to authorize access to dropbox.")
        
        return msg
    
    
    def finalize_connection(self,request_token):
        
        (app_key,app_secret,access_type) = self.get_dropbox_app_keys()
        sess = session.DropboxSession(app_key, app_secret, access_type)
        
        #once url has been loaded and access granted, this token can be used to access dropbox from now on
        try:
            access_token = sess.obtain_access_token(request_token)
        except ErrorResponse as e:
            return "finalize did not succeed: " + str(e)
                    
        #save access token to reuse later 
        self.access_token_key = access_token.key
        self.access_token_secret = access_token.secret
        self.save()
        
        return "Connection succeeded."
    

    
class ComicSiteFile(File):
    """
    A file which belongs to a certain ComicSite
    """
    
    def __init__(self,comicsite):
        self.comicsite = comicsite
    

class RegistrationRequestManager(models.Manager):
    """ adds some convenient queries to standard .objects()""" 
    
    def get_pending_registration_requests(self,user,site):
        """ So people can be shown that they have already sent a request and to make
        sure they don't (or some bot doesnt) request a 1000 times
        
        Return: RegistrationRequest object if it already exists, empty list if it 
        does not   
        """    
            
        return self.filter(project=site,
                           user=user,
                           status=RegistrationRequest.PENDING)
    
    def get_accepted_registration_requests(self,user,site):
        """ So people can be shown that they have already sent a request and to make
        sure they don't (or some bot doesnt) request a 1000 times
        
        Return: RegistrationRequest object if it already exists, empty list if it 
        does not   
        """
        return self.filter(project=site,
                           user=user,
                           status=RegistrationRequest.ACCEPTED)

        
    def get_query_set(self):
        
        return super(RegistrationRequestManager, self).get_query_set()





@track_data('status')
class RegistrationRequest(models.Model):
    """ When a user wants to join a project, admins have the option of reviewing
        each user before allowing or denying them. This class records the needed
        info for that. 
    """
    objects = RegistrationRequestManager()
    
    user = models.ForeignKey(User, help_text = "which user requested to participate?")
    project = models.ForeignKey(ComicSite, 
                                  help_text = "To which project does the user want to register?")
    
    created = models.DateTimeField(auto_now_add=True,default=datetime.date.today)
    changed = models.DateTimeField(blank=True,null=True)    
    
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
    
    
    #question: where to send email to admin? probably not here? 
    
    def __unicode__(self):
        """ describes this object in admin interface etc.
        """
        return "{1} registration request by user {0}".format(self.user.username,
                                                             self.project.short_name)
    
    def status_to_string(self):
        str = "Your participation request for " + self.project.short_name +\
                ", sent " + self.format_date(self.created)
                
        if self.status == self.PENDING:
            str += ", is awaiting review"
        elif self.status == self.ACCEPTED:
            str += ", was accepted at " + self.format_date(self.changed)
        elif self.status == self.REJECTED:
            str += ", was rejected at " + self.format_date(self.changed)
        
        return str
    
    def format_date(self,date):
        return date.strftime('%b %d, %Y at %H:%M')
    
    def user_real_name(self):        
        return self.user.first_name + " " + self.user.last_name 
    
    def user_email(self):        
        return self.user.email
    
    def user_affiliation(self):
        profile = self.user.user_profile 
        return profile.institution + " - " + profile.department
    
