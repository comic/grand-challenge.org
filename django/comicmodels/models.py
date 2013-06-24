import os
import re
import datetime
import pdb

from django import forms
from django.conf import settings
from django.contrib.auth.models import Group,User,Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files import File
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from django.db.models import Q
from django.utils.safestring import mark_safe

from ckeditor.fields import RichTextField
from dropbox import client, rest, session
from dropbox.rest import ErrorResponse
from guardian.shortcuts import assign,remove_perm

from dataproviders import FileSystemDataProvider,DropboxDataProvider


def giveFileUploadDestinationPath(uploadmodel,filename):
    """ Where should this file go relative to MEDIA_ROOT? """
    
    #uploadmodel can be either a ComicSiteModel, or a ComicSite
    if hasattr(uploadmodel,'short_name'):
        comicsitename = uploadmodel.short_name  # is a ComicSite
    else:
        comicsitename = uploadmodel.comicsite.short_name # is a ComicSiteModel
         
    path = os.path.join(comicsitename,"uploads",filename)    
    return path


def get_anonymous_user():
    """Anymous user is the default user for non logged in users. I is also the only member of group
      'everyone' for which permissions can be set """
    return User.objects.get(username = "anonymousUser")


class ComicSiteManager(models.Manager):
    """ adds some tabel level functions for getting ComicSites from db. """ 
    
    def non_hidden(self):
        """ like all(), but only return ComicSites for which hidden=false"""
        return self.filter(hidden=False)
    
    def get_query_set(self):
        
        return super(ComicSiteManager, self).get_query_set()
    
    

class ComicSite(models.Model):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    short_name = models.SlugField(max_length = 50, default="", help_text = "short name used in url, specific css, files etc. No spaces allowed")
    skin = models.CharField(max_length = 225, blank=True, help_text = "additional css to use for this comic site. Not required")    
    description = models.CharField(max_length = 1024, default="", blank=True,help_text = "Short summary of this project, max 1024 characters.")
    logo = models.URLField(help_text = "URL of a 200x200 image to use as logo for this comicsite in overviews",default="http://www.grand-challenge.org/images/a/a7/Grey.png")
    header_image = models.ImageField(default="", blank=True, upload_to=giveFileUploadDestinationPath, help_text = "Header which will appear on top of each project page")
    
    hidden = models.BooleanField(default=False, help_text = "Do not display this Project in any public overview")
    hide_signin = models.BooleanField(default=False, help_text = "Do no show the Sign in / Register link on any page")
    hide_footer = models.BooleanField(default=False, help_text = "Do not show the general links or the grey divider line in page footers")
    
    objects = ComicSiteManager()
    
    def __unicode__(self):
        """ string representation for this object"""
        return self.short_name
       
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        pass
        #TODO check whether short name is really clean and short!        
    
    def upload_dir(self):
        """Where to get and put uploaded files? """
        return os.path.join(settings.MEDIA_ROOT,self.short_name,"uploads")
         
            
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
        """ is user in the admins group for the comicsite to which this object belongs? superuser always passes        
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
        #admins = User.objects.filter(groups__name=self.admin_group_name(), is_superuser=False)        
        admins = User.objects.filter(groups__name=self.admin_group_name())
     
  
              

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
            object needs to be saved befor setting perms"""
        
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
        
    file = models.FileField(upload_to=giveFileUploadDestinationPath)
    user = models.ForeignKey(User, help_text = "which user uploaded this?")
    created = models.DateTimeField(auto_now_add=True,default=datetime.date.today) 
    modified = models.DateTimeField(auto_now=True,default=datetime.date.today)
    
    @property    
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1]
    
    @property
    def localfileexists(self):                     
        return os.path.exists(self.file.path)
    
    
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
    
        
    
    
