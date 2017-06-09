from django.core.storage import FileSystemStorage


class ProjectDataProvider(FileSystemStorage):
    """ FilesystemStorage provider which checks permissions based on project
    admin/participant group membership for different projects.      
    """

    def read(self, filename):
        return self.client.get_file(filename).read()
