from django.conf.urls import patterns, include, url
from django.views.generic import ListView
from django.contrib import admin
from ComicSite.models import ComicSite
from django.views.generic.simple import redirect_to 

admin.autodiscover()

# prefix introduced to make it possible to serve django from non-root dir on server.
# see https://github.com/comic/comic-django/issues/14 
urlPrefix = ""

urlpatterns = patterns('',
    
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # for convenience in developing: redirect to not have to type /Comic 
    # after 'localhost' to load site for the first time
    #(r'^$', redirect_to, {'url': '/'+urlPrefix}),
     
    # Uncomment the next line to enable the admin:
    url(r'^'+urlPrefix+'admin/', include(admin.site.urls)),
    
    # main page 
    url(r'^'+urlPrefix+'$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
    
    #specific view of single comicsite
    url(r'^'+urlPrefix+'site/(?P<site_name>\w+)/$','ComicSite.views.site'),
    
    url(r'^'+urlPrefix+'site/(?P<site_name>\w+)/(?P<page_title>\w+)/$','ComicSite.views.page'),
    
    
    url(r'^'+urlPrefix+'test/showData/$','ComicSite.views.dataPage'),
    
    #url(r'^site/(?P<site_name>\w+)/(?P<page_title>\w+)/$','ComicSite.views.page'),
)
    