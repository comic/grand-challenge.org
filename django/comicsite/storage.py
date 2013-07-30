import StringIO
import os
import pdb

from django.core.files.storage import FileSystemStorage
from django.core.files import File


from django.conf import settings



class MockStorage(FileSystemStorage):
    """
    For testing, A storage class which does not write anything to disk.
    """
    
    # For testing, any dir in FAKE DIRS will exist and contain FAKE_FILES         
    FAKE_DIRS = ["fake_test_dir",
                 settings.COMIC_PUBLIC_FOLDER_NAME,
                 settings.COMIC_REGISTERED_ONLY_FOLDER_NAME
                 ]
                 
    
    FAKE_FILES = ["fakefile1.txt",
                  "fakefile2.jpg",
                  "fakefile3.exe",
                  "fakesfile4.mhd"]

    def _save(self, name, content):
        # do NOTHING
        return name
    
    def _open(self, name, mode='rb'):
        """ Return a memory only file which will not be saved to disk
        
        """
        mockfile = File(StringIO.StringIO("mock content")) 
        mockfile.name = "MOCKED_FILE_"+name
        return mockfile
            
    def delete(self, name):
        pass

    def exists(self, name):
        """ Any file in FAKE_FILES exists if one of the FAKE_DIRS are in its 
        path. A path exists any of FAKE_DIRS is in its path          
        """
        
        dir,file_or_folder = os.path.split(name)
        if "." in file_or_folder: #input was a file path
             return self.is_in_fake_test_dir(dir) and (file_or_folder in self.FAKE_FILES)
        else: #input was a directory path
            return self.is_in_fake_test_dir(name) 
        

    def listdir(self, path):        
        if self.is_in_fake_test_dir(path):
            directories = []
            files = self.FAKE_FILES        
        else:
            if self.exists(path):
                directories, files = [], []
            else:
                #"This is what default storage would do when listing a non 
                # existant dir "
                raise OSError("Directory does not exist")            
            
        
        return directories, files

    def path(self, name):
        return name

    def size(self, name):
        if self.is_in_fake_test_dir(name) & (os.path.split(name)[1] in self.FAKE_FILES):
            return 10000
        else:
            return 0
    
    def is_in_fake_test_dir(self,path):
        """ Is this file in the special fake directory? This dir does not exist
        on disk but returns some values anyway. For testing.
        
        """
        for dir in self.FAKE_DIRS:
            if dir in path: #very rough test. But this is only for testing
                return True
                    
        return False
        
        
    
    

        

