import Image
import pdb
import os
import StringIO
from io import BytesIO


from django.core.files.storage import FileSystemStorage
from django.core.files import File


from django.conf import settings


def fake_file(filename,content="mock content"):
        """ For testing I sometimes want specific file request to return 
        specific content. This is make creation easier 
        """
        return {"filename":filename,"content":content}

class MockStorage(FileSystemStorage):
    """
    For testing, A storage class which does not write anything to disk.
    """
    
    # For testing, any dir in FAKE DIRS will exist and contain FAKE_FILES         
    FAKE_DIRS = ["fake_test_dir",
                 settings.COMIC_PUBLIC_FOLDER_NAME,
                 settings.COMIC_REGISTERED_ONLY_FOLDER_NAME
                 ]
                 
    
    FAKE_FILES = [fake_file("fakefile1.txt"),
                  fake_file("fakefile2.jpg"),
                  fake_file("fakefile3.exe"),
                  fake_file("fakefile4.mhd"),
                  fake_file("fakecss.css","body {width:300px;}")]

    def _save(self, name, content):
        # do NOTHING
        return name
    
    def _open(self, path, mode='rb'):
        """ Return a memory only file which will not be saved to disk
        If an image is requested, fake image content using PIL
        
        """        
        if os.path.splitext(path)[1].lower() in [".jpg",".png",".gif",".bmp"]:
            #1px test image
            binary_image_data = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdb\x0c\x17\x020;\xd1\xda\xcf\xd2\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
            
            img = BytesIO(binary_image_data)
            mockfile = File(img)
            mockfile.name = "MOCKED_IMAGE_"+path
        else:
            
            content = "mock content"
            # If a predefined fake file is asked for, return predefined content            
            filename = os.path.split(path)[1]            
            for mockfilename,mockcontent in self.FAKE_FILES:
               if filename == mockfilename:
                   content = mockcontent
                            
            mockfile = File(StringIO.StringIO(content)) 
            mockfile.name = "MOCKED_FILE_"+path
        
        
        return mockfile
    
    
    def delete(self, name):
        pass

    def exists(self, name):
        """ Any file in FAKE_FILES exists if one of the FAKE_DIRS are in its 
        path. A path exists any of FAKE_DIRS is in its path          
        """                
        if name.endswith("/"):
            name = name[:-1]
        dir,file_or_folder = os.path.split(name)        
        if "." in file_or_folder: #input was a file path
             filenames = [x["filename"] for x in self.FAKE_FILES]
             return self.is_in_fake_test_dir(dir) and (file_or_folder in filenames)
        else: #input was a directory path
            return self.is_in_fake_test_dir(name) 
        

    def listdir(self, path):        
        if self.is_in_fake_test_dir(path):
            directories = []
            files = [x["filename"] for x in self.FAKE_FILES]
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
        filenames = [x["filename"] for x in self.FAKE_FILES]
        if self.is_in_fake_test_dir(name) & (os.path.split(name)[1] in filenames):
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
        
        
    
    

        

