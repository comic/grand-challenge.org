import os
import re
import pdb

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
    title = models.CharField(max_length=64, blank=True)
    description = models.TextField()
    comicsite = models.ForeignKey(ComicSite)
    
       
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
    folder = models.FilePathField(editable=False)
        
    def get_all_files(self):
        """ return array of all files in this folder
        """        
        dp = FileSystemDataProvider.FileSystemDataProvider(self.folder)
        filenames = dp.getFileNames()
        htmlOut = "available files:"+", ".join(filenames)
        return htmlOut

    
    def save(self):                    
        data_dir = self.get_data_dir()
        self.ensure_dir(data_dir)
        self.folder = data_dir
        super(FileSystemDataset,self).save()
        
    
    def get_data_dir(self):
        """ In which dir should this dataset be located? Return full path  
        """        
        
        data_dir_path = os.path.join(settings.MEDIA_ROOT,self.comicsite.short_name,self.cleantitle)
        #data_dir_path = os.path.join(self.comicsite.short_name,self.cleantitle)
        return data_dir_path
    
    def get_relative_data_dir(self):
        """ In which dir Where should this dataset be located?  Return relative to MEDIA_ROOT
        """        
        
        data_dir_path = os.path.join(self.comicsite.short_name,self.cleantitle)
        return data_dir_path
    
    def ensure_dir(self,dir):
        if not os.path.exists(dir):
            os.makedirs(dir)


        
     