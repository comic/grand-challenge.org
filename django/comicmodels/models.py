import os
import re
import pdb

from django import forms
from django.db import models
from django.conf import settings


from dataproviders import FileSystemDataProvider
from comicsite.models import ComicSite 

class UploadModel(models.Model):
    
    title = models.CharField(max_length=64, blank=True)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/%H/%M/%S/')

    @property    
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1]
    
    
class Dataset(models.Model):
    """
    Collection of files 
    """
    title = models.CharField(max_length=64, blank=True, help_text = "short name used to refer to this dataset, do not use spaces")
    description = models.TextField()
    comicsite = models.ForeignKey(ComicSite, help_text = "To which comicsite does this dataset belong? Used to determine permissions")
    
       
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
            data_dir = self.get_relative_data_dir()
        else:
            # take possibly edited value from form
            data_dir = self.folder
                       
        pdb.set_trace()
        self.ensure_dir(self.get_default_data_dir())
        self.folder = data_dir
        super(FileSystemDataset,self).save()
        
    
    def get_default_data_dir(self):
        """ In which dir should this dataset be located? Return full path  
        """                        
        data_dir_path = os.path.join(settings.MEDIA_ROOT,self.get_relative_data_dir())
        #data_dir_path = os.path.join(self.comicsite.short_name,self.cleantitle)
        return data_dir_path
    
    def get_relative_data_dir(self):
        """ In which dir Where should this dataset be located?  Return relative to MEDIA_ROOT
        """        
        
        data_dir_path = os.path.join(self.folder_prefix,self.comicsite.short_name,self.cleantitle)
        return data_dir_path
    
    def ensure_dir(self,dir):
        if not os.path.exists(dir):
            os.makedirs(dir)


        
     