from django.conf.urls import url, include
from django.views.generic import TemplateView, RedirectView

from grandchallenge.core.api import get_public_results
from grandchallenge.core.views import site
from uploads.views import serve

urlpatterns = [
    url(
        r'^(?P<challenge_short_name>[\w-]+)/$', site, name='challenge-homepage'
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/robots\.txt/$', 
        TemplateView.as_view(
            template_name='robots.txt', content_type='text/plain'
        ), 
        name="comicsite_robots_txt"
    ),
    # Note: add new namespaces to comic_URLNode(defaulttags.URLNode)
    url(
        r'^(?P<challenge_short_name>[\w-]+)/evaluation/',
        include('grandchallenge.evaluation.urls', namespace='evaluation'),
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/teams/',
        include('teams.urls', namespace='teams'),
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/participants/',
        include('participants.urls', namespace='participants'),
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/admins/',
        include('grandchallenge.admins.urls', namespace='admins'),
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/uploads/', 
        include('uploads.urls', namespace='uploads')
    ),
    #################
    #
    # Legacy apps
    #
    url(
        r'^(?P<challenge_short_name>[\w-]+)/files/$',
        RedirectView.as_view(pattern_name='uploads:create', permanent=False),
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/serve/(?P<path>.+)/$',
        serve,
        name="project_serve_file",
    ),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/api/get_public_results/$', 
        get_public_results
    ),
    # 
    # End Legacy
    #
    #################
    # If nothing specific matches, try to resolve the url as project/pagename
    url(
        r'^(?P<challenge_short_name>[\w-]+)/',
        include('grandchallenge.pages.urls', namespace='pages'),
    ),
]
