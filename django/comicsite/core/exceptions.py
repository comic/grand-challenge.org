"""
Things that can go wrong specifically in this framework 
"""

class ComicException(Exception):
    pass 

class ProjectAdminException(ComicException):
    "Something went wrong in the project-centered admin interface"

