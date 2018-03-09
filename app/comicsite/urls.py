from django.conf.urls import url, include
from django.views.generic import TemplateView

from comicmodels.views import upload_handler
from comicsite.admin import projectadminurls
from comicsite.api import get_public_results
from comicsite.views import site
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

    url(
        r'^(?P<site_short_name>[\w-]+)/robots\.txt/$',
        TemplateView.as_view(
            template_name='robots.txt',
            content_type='text/plain',
        ),
        name="comicsite_robots_txt",
    ),

    # Note: add new namespaces to comic_URLNode(defaulttags.URLNode)

    url(r'^(?P<challenge_short_name>[\w-]+)/evaluation/',
        include('evaluation.urls', namespace='evaluation')),

    url(r'^(?P<challenge_short_name>[\w-]+)/teams/',
        include('teams.urls', namespace='teams')),

    url(r'^(?P<challenge_short_name>[\w-]+)/participants/',
        include('participants.urls', namespace='participants')),

    url(r'^(?P<challenge_short_name>[\w-]+)/admins/',
        include('admins.urls', namespace='admins')),

    url(r'^(?P<site_short_name>[\w-]+)/ckeditor/', include('ckeditor.urls')),

    url(r'^(?P<site_short_name>[\w-]+)/files/$', upload_handler,
        name='challenge-upload-handler'),

    url(r'^(?P<project_name>[\w-]+)/serve/(?P<path>.+)/$', serve,
        name="project_serve_file"),

    url(r'^(?P<project_name>[\w-]+)/api/get_public_results/$',
        get_public_results),

    # If nothing specific matches, try to resolve the url as project/pagename
    url(r'^(?P<challenge_short_name>[\w-]+)/',
        include('pages.urls', namespace='pages')),
]
