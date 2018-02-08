"""
 Custom processors to pass variables to views rendering template tags 
 see http://www.djangobook.com/en/2.0/chapter09.html  
"""
from django.conf import settings
from django.core.urlresolvers import resolve
from django.http import Http404

from comicmodels.models import ComicSite
from comicsite.utils import build_absolute_uri
from comicsite.views import site_get_standard_vars


def comic_site(request):
    """ Find out in which comic site this request is loaded. If you cannot
    figure it out. Use main project. 
    
    """

    try:
        resolution = resolve(request.path)
    except Http404 as e:
        # fail silently beacuse any exeception here will cause a 500 server error
        # on page. Let views show errors but not the context processor
        resolution = resolve("/")

    if "site_short_name" in resolution.kwargs:
        sitename = resolution.kwargs["site_short_name"]
    elif "project_name" in resolution.kwargs:
        sitename = resolution.kwargs["project_name"]
    elif "challenge_short_name" in resolution.kwargs:
        sitename = resolution.kwargs["challenge_short_name"]
    else:
        sitename = settings.MAIN_PROJECT_NAME

    try:
        [site, pages, metafooterpages] = site_get_standard_vars(sitename)
    except ComicSite.DoesNotExist:
        # Don't crash the system here, if a site cannot be found it will crash 
        # in a more appropriate location
        return {}

    return {
        "site": site,
        "user_is_participant": site.is_participant(request.user),
        "pages": pages,
        "metafooterpages": metafooterpages,
        "main_project_name": settings.MAIN_PROJECT_NAME,
    }


def subdomain_absolute_uri(request):
    uri = build_absolute_uri(request)

    return {'subdomain_absolute_uri': uri}
