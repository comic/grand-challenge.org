class ComicException(Exception):
    pass


class PathResolutionException(ComicException):
    """ A path given to a COMIC template tag contained variables that could not
        be resolved
    """
