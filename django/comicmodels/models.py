import os
import re
import pdb

from django import forms
from django.conf import settings
from django.contrib.auth.models import Group,User,Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models




from dataproviders import FileSystemDataProvider
 


def giveFileUploadDestinationPath(uploadmodel,filename):
    """ Where should this file go relative to MEDIA_ROOT? """
    
    path = os.path.join(uploadmodel.comicsite.short_name,"uploads",filename)    
    return path


def get_anonymous_user():
    """Anymous user is the default user for non logged in users. I is also the only member of group
      'everyone' for which permissions can be set """
    return User.objects.get(username = "anonymousUser")


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


        
     