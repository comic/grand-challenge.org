from django.conf.urls import patterns, include, url
from django.views.generic import ListView
from django.contrib import admin
from ComicSite.models import ComicSite 

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'comic.views.home', name='home'),
    # url(r'^comic/', include('comic.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    
    # main page 
    url(r'^$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
    
    #specific view of single comicsite
    url(r'^site/(?P<site_id>\d+)/$','ComicSite.views.site'),
)
    