"""
Things that can go wrong specifically in this framework 
"""


class ComicException(Exception):
    pass


class ProjectAdminException(ComicException):
    """Something went wrong in the project-centered admin interface"""


class ParserException(ComicException):
    """ Error trying to parse some file included on a project page"""


class PathResolutionException(ComicException):
    """ A path given to a COMIC template tag contained variables that could not
        be resolved
    """
