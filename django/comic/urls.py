from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic import ListView,TemplateView
from django.contrib import admin
from comicmodels.models	 import ComicSite

 
admin.autodiscover()


urlpatterns = patterns('',
    
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # main page 
    url(r'^$','comicsite.views.comicmain',name = 'home'),
    #url(r'^Comic/$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
    
    # tell nice bots what to do. TODO: using 'robots.txt' as a template name will
    # give a 404.  WHY?
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.html')),
    
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
    
    # Submit a project for addition to the projects overview
    url(r'^submit_existing_project/$','comicsite.views.submit_existing_project'),
    
    # some methods for dealing with dropbox folders. Used to make asynchronous calls from admin.
    url(r'^django_dropbox/',include('django_dropbox.urls')),
    
    # WYSIWYG editor for HTML
    (r'^ckeditor/', include('ckeditor.urls')),
    
    # ========== catch all ====================
    # when all other urls have been checked, try to load page from main project
    # keep this url at the bottom of this list, because urls are checked in order 
    url(r'^(?P<page_title>[\w-]+)/$','comicsite.views.comicmain'),
    
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))
else:
    urlpatterns += patterns('',
        (r'^media/(?P<project_name>[\w-]+)/(?P<path>.*)$', 'filetransfers.views.serve', {
        'document_root': settings.MEDIA_ROOT}))
