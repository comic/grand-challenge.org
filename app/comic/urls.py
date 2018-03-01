from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView

from comicmodels.views import ChallengeCreate
from comicsite.views import comicmain
from filetransfers.views import serve

admin.autodiscover()

urlpatterns = [

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # main page
    url(r'^$', comicmain, name='home'),
    # url(r'^Comic/$',ListView.as_view(model=ComicSite,
    # template_name='index.html'),name = 'home'),

    # tell nice bots what to do. TODO: using 'robots.txt' as a template name
    #  will
    # give a 404.  WHY?
    url(r'^robots\.txt/$', TemplateView.as_view(template_name='robots.html')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^site/', include('comicsite.urls'), name='site'),

    url(r'^filetransfers/', include('filetransfers.urls', namespace='filetransfers')),

    # Do not change the namespace without updating the view names in
    # evaluation.serializers
    url(r'^api/', include('api.urls', namespace='api')),

    # Used for logging in and managing profiles. This is done on the framework
    # level because it is too hard to get this all under each project
    url(r'^accounts/', include('profiles.urls')),
    url(r'^socialauth/', include('social_django.urls', namespace='social')),

    # WYSIWYG editor for HTML
    url(r'^ckeditor/', include('ckeditor.urls')),

    url(r'^create_challenge/$', ChallengeCreate.as_view(),
        name='challenge_create'),

    # ========== catch all ====================
    # when all other urls have been checked, try to load page from main project
    # keep this url at the bottom of this list, because urls are checked in
    # order
    url(r'^(?P<page_title>[\w-]+)/$', comicmain, name='mainproject-home'),

    url(r'^media/(?P<project_name>[\w-]+)/(?P<path>.*)$', serve),

]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
                      url(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns
