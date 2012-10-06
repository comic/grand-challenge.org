import os
import re
import pdb

from django import forms
from django.conf import settings
from django.contrib.auth.models import Group,User,Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.db.models import Q
from django.utils.safestring import mark_safe

from guardian.shortcuts import assign

from dataproviders import FileSystemDataProvider











def giveFileUploadDestinationPath(uploadmodel,filename):
    """ Where should this file go relative to MEDIA_ROOT? """
    
    path = os.path.join(uploadmodel.comicsite.short_name,"uploads",filename)    
    return path


def get_anonymous_user():
    """Anymous user is the default user for non logged in users. I is also the only member of group
      'everyone' for which permissions can be set """
    return User.objects.get(username = "anonymousUser")


class ComicSite(models.Model):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    short_name = models.CharField(max_length = 50, default="", help_text = "short name used in url, specific css, files etc. No spaces allowed")
    skin = models.CharField(max_length = 225)    
    description = models.CharField(max_length = 1024, default="", blank=True,help_text = "Short summary of this project, max 1024 characters.")
    logo = models.URLField(help_text = "URL of a 200x200 image to use as logo for this comicsite in overviews",default="")
        
    def __unicode__(self):
        """ string representation for this object"""
        return self.short_name
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        #TODO check whether short name is really clean and short!
            
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
    
    

class ComicSiteModel(models.Model):
    """An object which can be shown or used in the comicsite framework. This base class should handle common functions
     such as authorization.
    """
    #user = models.ManyToManyField()
    title = models.CharField(max_length=64, blank=True)
    comicsite = models.ForeignKey(ComicSite, help_text = "To which comicsite does this file belong? Used to determine permissions")
    # = models.CharField(max_length=64, blank=True)
        
    
    def __unicode__(self):
       """ string representation for this object"""
       return self.title
   
    def can_be_viewed_by(self,user):
        """ boolean, is user allowed to view this? """
        
        # check whether everyone is allowed to view this. Anymous user is the only member of group
        # 'everyone' for which permissions can be set
        anonymousUser = get_anonymous_user()
        #pdb.set_trace()        
        
        if anonymousUser.has_perm("view_ComicSiteModel",self):
            return True
        else:
            # if not everyone has access, check whether given user has permissions
            return user.has_perm("view_ComicSiteModel",self)
        
        
    class Meta:
       abstract = True
       permissions = (("view_ComicSiteModel", "Can view Comic Site Model"),)


class Page(ComicSiteModel):
    """ A single editable page containing html and maybe special output plugins """
    
    order = models.IntegerField(editable=False, default=1, help_text = "Determines order in which page appear in site menu")        
    display_title = models.CharField(max_length = 255, default="", blank=True, help_text = "On pages and in menu items, use this text. Spaces and special chars allowed here. Optional field. If emtpy, title is used")
    hidden = models.BooleanField(default=False, help_text = "Do not display this page in site menu")
 
    html = models.TextField()
    
    
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
            mm = Page.objects.get(ComicSite=self.comicsite,order=self.order-1)
            mm.order += 1
            mm.save()
            self.order -= 1
            self.save()
        if move == 'DOWN':
            mm = Page.objects.get(ComicSite=self.comicsite,order=self.order+1)
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




class UploadModel(ComicSiteModel):
        
    file = models.FileField(upload_to=giveFileUploadDestinationPath)
    
    
    @property    
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1]
    
    class Meta(ComicSiteModel.Meta):
        verbose_name = "uploaded file"
        verbose_name_plural = "uploaded files"
        

    
class Dataset(models.Model):
    """
    Collection of files
    """
    title = models.CharField(max_length=64, blank=True, help_text = "short name used to refer to this dataset, do not use spaces")
    description = models.TextField()
    comicsite = models.ForeignKey(ComicSite, default=None, help_text = "To which comicsite does this dataset belong? Used to determine permissions")
    
       
    @property
    def cleantitle(self):
        return re.sub('[\[\]/{}., ]+', '',self.title)
   
    def __unicode__(self):
       """ string representation for this object"""
       return self.title
                
    class Meta:
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

    
    def save(self):
        #when saving for the first time only 
        if not self.id:
            # initialize data dir 
            data_dir = self.get_default_data_dir()
            self.folder = data_dir            
        else:
            # take possibly edited value from form, keep self.folder.
            pass
                                                       
        self.ensure_dir(self.folder)        
        super(FileSystemDataset,self).save()
        
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
        return "{% dataset " + self.comicsite.short_name + "," + self.cleantitle + " %}" 
        
    
    
    def ensure_dir(self,dir):
        if not os.path.exists(dir):
            os.makedirs(dir)        


        
     