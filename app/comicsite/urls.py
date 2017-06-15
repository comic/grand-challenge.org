from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView

from comicsite.admin import projectadminurls
from profiles.forms import SignupFormExtra

urlpatterns = patterns('',

                       url(r'^(?P<site_short_name>[\w-]+)/$', 'comicsite.views.site'),

                       # Include an admin url for each project in database. This stretches the django
                       # Assumptions of urls being fixed a bit, but it is the only way to reuse much
                       # of the automatic admin functionality whithout rewriting the whole interface
                       # see issue #181
                       url(r'^', include(projectadminurls.allurls), name='projectadmin'),

                       url(r'^(?P<site_short_name>[\w-]+)/robots\.txt/$',
                           TemplateView.as_view(template_name='robots.html'), name="comicsite_robots_txt"),

                       url(r'^(?P<site_short_name>[\w-]+)/ckeditor/', include('ckeditor.urls')),

                       # these registration and account views are viewed in the context of a
                       # project
                       url(r'^(?P<site_short_name>[\w-]+)/accounts/signin/$', 'comicsite.views.signin',
                           name="comicsite_signin"),
                       url(r'^(?P<site_short_name>[\w-]+)/accounts/signup/$', 'comicsite.views.signup',
                           {'signup_form': SignupFormExtra}, name="comicsite_signup"),
                       url(r'^(?P<site_short_name>[\w-]+)/accounts/signup_complete/$',
                           'comicsite.views.signup_complete', name="comicsite_signup_complete"),

                       url(r'^(?P<site_short_name>[\w-]+)/files/$', 'comicmodels.views.upload_handler'),

                       url(r'^(?P<project_name>[\w-]+)/serve/(?P<path>.+)/$', 'filetransfers.views.serve',
                           name="project_serve_file"),

                       url(r'^(?P<site_short_name>[\w-]+)/_request_participation/$', 'comicsite.views._register'),

                       url(r'^(?P<site_short_name>[\w-]+)/source/(?P<page_title>[\w-]+)/$',
                           'comicsite.views.pagesource'),

                       url(r'^(?P<project_name>[\w-]+)/api/get_public_results/$', 'comicsite.api.get_public_results'),

                       url(r'^(?P<site_short_name>[\w-]+)/(?P<page_title>[\w-]+)/insert/(?P<dropboxpath>.+)/$',
                           'comicsite.views.insertedpage'),

                       # If nothing specific matches, try to resove the url as project/pagename
                       url(r'^(?P<site_short_name>[\w-]+)/(?P<page_title>[\w-]+)/$', 'comicsite.views.page'),
                       )
