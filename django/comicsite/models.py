    
    
class ComicSiteException(Exception):
    """ any type of exception for which a django or python exception is not defined """
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)
    
    
