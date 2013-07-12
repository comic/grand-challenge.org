import StringIO
from django.core.files.storage import FileSystemStorage
from django.core.files import File



class MockStorage(FileSystemStorage):
    """
    For testing, A storage class which does not write anything to disk.
    """

    def _save(self, name, content):
        # dp NOTHING
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
        return False

    def listdir(self, path):
        path = path
        directories, files = [], []            
        return directories, files

    def path(self, name):
        return name

    def size(self, name):
        return 0

        

