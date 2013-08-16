"""
 Custom processors to pass variables to views rendering template tags 
 see http://www.djangobook.com/en/2.0/chapter09.html  
"""

from django.template import RequestContext
from django.conf import settings

from comicsite.views import getSite

def comic_site(request):
    """ Find out in which comic site this request is loaded. If you cannot
    figure it out. Use main project. 
    
    """
        
    from django.core.urlresolvers import resolve
    resolution = resolve(request.path)
        
    if resolution.kwargs.has_key("site_short_name"):
        sitename = resolution.kwargs["site_short_name"]
    elif resolution.kwargs.has_key("project_name"):
        sitename = resolution.kwargs["project_name"]
    else:
        sitename = settings.MAIN_PROJECT_NAME
    
    return {"site":getSite(sitename)}
        