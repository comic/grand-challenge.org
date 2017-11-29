"""
 Custom processors to pass variables to views rendering template tags 
 see http://www.djangobook.com/en/2.0/chapter09.html  
"""
import re
from django.conf import settings
from django.core.urlresolvers import resolve
from django.http import Http404

from comicmodels.models import ComicSite
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

    return {"site": site, "pages": pages, "metafooterpages": metafooterpages,
            "main_project_name": settings.MAIN_PROJECT_NAME}


def subdomain_absolute_uri(request):
    """
    Total hack to get around SUBDOMAN_IS_PROJECTNAME for absolute urls
    """
    subdomain_absolute_uri = request.build_absolute_uri()

    if settings.SUBDOMAIN_IS_PROJECTNAME:
        try:
            m = re.search(
                r'\/\/(?P<host>[^\/]+)\/site\/(?P<subdomain>[^\/]+)\/',
                subdomain_absolute_uri + '/')
            host = m['host']
            subdomain = m['subdomain']
            subdomain_absolute_uri = subdomain_absolute_uri[:m.start(0)] \
                                     + '//' \
                                     + subdomain \
                                     + '.' \
                                     + host \
                                     + '/' \
                                     + subdomain_absolute_uri[m.end(0):]
        except TypeError:
            # nothing to rewrite
            pass

    return {'subdomain_absolute_uri': subdomain_absolute_uri}
