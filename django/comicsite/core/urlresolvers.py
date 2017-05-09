from django.core.urlresolvers import reverse as reverse_org
from comic import settings
from comicsite.templatetags.comic_templatetags import subdomain_is_projectname


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