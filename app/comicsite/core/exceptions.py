"""
Things that can go wrong specifically in this framework 
"""


class ComicException(Exception):
    pass


class ParserException(ComicException):
    """ Error trying to parse some file included on a project page"""


class PathResolutionException(ComicException):
    """ A path given to a COMIC template tag contained variables that could not
        be resolved
    """
