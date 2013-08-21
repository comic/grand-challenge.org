from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic import ListView
from django.contrib import admin
from comicmodels.models	 import ComicSite

 
admin.autodiscover()


urlpatterns = patterns('',
    
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # main page 
    url(r'^$','comicsite.views.comicmain',name = 'home'),
    #url(r'^Comic/$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
     
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
      
    url(r'^site/',include('comicsite.urls'),name='site'),
    
    url(r'^projectlinks/$','comicsite.views.projectlinks'),

    url(r'^filetransfers/',include('filetransfers.urls')),
    
    # Used for logging in and managing profiles. This is done on the framework
    # level because it is too hard to get this all under each project 
    url(r'^accounts/',include('profiles.urls')),
    url(r'^socialauth/',include('social_auth.urls')),
    
    #temporary url to test MeVisLab visualisation. This should be moved to a seperate MeVis app
    url(r'^mevislab_visualisation', 'mevislab_visualisation.views.index'),
    
    # when all other urls have been checked, try to load page from main project
    # keep this url at the bottom of this list, because urls are checked in order 
    url(r'^(?P<page_title>\w+)/$','comicsite.views.comicmain'),
    
    # some methods for dealing with dropbox folders. Used to make asynchronous calls from admin.
    url(r'^django_dropbox/',include('django_dropbox.urls')),
    
    # WYSIWYG editor for HTML
    (r'^ckeditor/', include('ckeditor.urls')),
    
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))
else:
    urlpatterns += patterns('',
        (r'^media/(?P<project_name>\w+)/(?P<path>.*)$', 'filetransfers.views.serve', {
        'document_root': settings.MEDIA_ROOT}))
