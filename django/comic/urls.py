from django.conf.urls import patterns, include, url
from django.views.generic import ListView
from django.contrib import admin
from comicsite.models import ComicSite
from django.views.generic.simple import redirect_to

 
admin.autodiscover()


urlpatterns = patterns('',
    
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),


    # main page 
    url(r'^$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
    #url(r'^Comic/$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
     
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
        
    #when viewing a site, redirect to /home page for that site
    url(r'^site/(?P<site_short_name>\w+)/$', redirect_to, {'url': '/site/%(site_short_name)s/Home'}),
    
    #this one is needed to be able make {% url work}  TODO: having two identical regexes here seems stinky.. can this be different?    
    url(r'^site/(?P<site_short_name>\w+)/$','comicsite.views.site'),
    
    url(r'^site/(?P<site_short_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),

    url(r'^test/showData/$','comicsite.views.dataPage'),
    
    # requirement for social_auth
    #url(r'',include('social_auth.urls')),
)
    
