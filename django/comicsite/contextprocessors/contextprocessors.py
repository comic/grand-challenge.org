"""
 Custom processors to pass variables to views rendering template tags 
 see http://www.djangobook.com/en/2.0/chapter09.html  
"""

from django.template import RequestContext
from django.conf import settings
from django.core.urlresolvers import resolve

from comicsite.views import site_get_standard_vars
from django.http import Http404


def comic_site(request):
    """ Find out in which comic site this request is loaded. If you cannot
    figure it out. Use main project. 
    
    """
    
    try:
        resolution = resolve(request.path)
    except Http404 as e:
        #fail silently beacuse any exeception here will cause a 500 server error
        # on page. Let views show errors but not the context processor
        resolution = resolve("/")
                        
    if resolution.kwargs.has_key("site_short_name"):
        sitename = resolution.kwargs["site_short_name"]
    elif resolution.kwargs.has_key("project_name"):
        sitename = resolution.kwargs["project_name"]
    else:
        sitename = settings.MAIN_PROJECT_NAME
    
    [site, pages, metafooterpages] = site_get_standard_vars(sitename)
    
    return {"site":site,"pages":pages,"metafooterpages":metafooterpages}
        