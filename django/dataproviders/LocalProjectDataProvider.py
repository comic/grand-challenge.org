import pdb
import re
import os

from django.core.storage import FileSystemStorage




class LocalProjectDataProvider(FileSystemStorage):
    """ FilesystemStorage provider which reads from the subfolder for the given project rather than MEDIA_ROOT     
    """


    def read(self, filename):
        return self.client.get_file(filename).read()


 
