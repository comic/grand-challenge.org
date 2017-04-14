from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse as reverse_org
from comic import settings



def subdomain_is_projectname():
    """ Check whether this setting is true in settings. Return false if not found

    """
    if hasattr(settings,"SUBDOMAIN_IS_PROJECTNAME"):
        subdomain_is_projectname = settings.SUBDOMAIN_IS_PROJECTNAME
        if subdomain_is_projectname and not hasattr(settings,"MAIN_HOST_NAME"):
            msg = """Key 'SUBDOMAIN_IS_PROJECTNAME' was defined in settings,
             but 'MAIN_HOST_NAME' was not. These belong together. Please
             add 'MAIN_HOST_NAME' and set it to the hostname of your site."""
            raise ImproperlyConfigured(msg)
    else:
        subdomain_is_projectname = False

    return subdomain_is_projectname

def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    """ Reverse url, but try to use subdomain to designate site where possible.
    This means 'site1' will not get url 'hostname/site/site1' but rather 'projectname.hostname'
    
    I am not certain that this is the most elegant way to do this. However this will
    currently solve the problem of links in projects overview being of the wrong kind 
    """
    # TODO: The final clause in the if statement is a total hack. May posterity 
    # forgive me for this method.
    # What is needed is a clear and unanbiguous way to deal with subdomain as project name
    # See for example the custom url template tag in comicsite.templatetags, which 
    # does almost the same as this method but in an even more complex way. Both
    # These methods should be refactored until they shine.  
    
    if viewname == 'comicsite.views.site' and subdomain_is_projectname() and args[0] is not None:
        protocol,domainname = settings.MAIN_HOST_NAME.split("//")
        url = protocol + "//" +args[0] +"."+ domainname
        
        return url    
    else:
        return reverse_org(viewname, urlconf, args, kwargs, prefix, current_app)