from django.db import models

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
        
    def get_all_files(self):
         """ return array of all files in this folder
         """
         dp = FileSystemDataProvider.FileSystemDataProvider(self.folder)
         filenames = dp.getFileNames()
         htmlOut = "available files:"+", ".join(filenames)
         return htmlOut
         

     