from django.conf.urls import url, include
from django.views.generic import TemplateView

from comicmodels.views import upload_handler
from comicsite.admin import projectadminurls
from comicsite.api import get_public_results
from comicsite.views import (
    ParticipantRegistration,
    site,
    _register,
)
from filetransfers.views import serve

urlpatterns = [

    url(r'^(?P<site_short_name>[\w-]+)/$', site,
        name='challenge-homepage'),

    # Include an admin url for each project in database. This stretches the
    # django
    # Assumptions of urls being fixed a bit, but it is the only way to reuse
    #  much
    # of the automatic admin functionality whithout rewriting the whole
    # interface
    # see issue #181
    url(r'^', include(projectadminurls.allurls), name='projectadmin'),

    url(r'^(?P<site_short_name>[\w-]+)/robots\.txt/$',
        TemplateView.as_view(template_name='robots.html'),
        name="comicsite_robots_txt"),

    url(r'^(?P<challenge_short_name>[\w-]+)/evaluation/',
        include('evaluation.urls', namespace='evaluation')),

    url(r'^(?P<challenge_short_name>[\w-]+)/teams/',
        include('teams.urls', namespace='teams')),

    url(r'^(?P<site_short_name>[\w-]+)/ckeditor/', include('ckeditor.urls')),

    url(r'^(?P<site_short_name>[\w-]+)/files/$', upload_handler,
        name='challenge-upload-handler'),

    url(r'^(?P<project_name>[\w-]+)/serve/(?P<path>.+)/$', serve,
        name="project_serve_file"),

    url(r'^(?P<project_name>[\w-]+)/api/get_public_results/$',
        get_public_results),

    url(r'^(?P<challenge_short_name>[\w-]+)/participant-registration/$',
        ParticipantRegistration.as_view(), name='participant-registration'),

    url(r'^(?P<site_short_name>[\w-]+)/_request_participation/$',
        _register, name='participant-registration-request'),

    # If nothing specific matches, try to resolve the url as project/pagename
    url(r'^(?P<site_short_name>[\w-]+)/(?P<page_title>[\w-]+)/',
        include('pages.urls')),
]
