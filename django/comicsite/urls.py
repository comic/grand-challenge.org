from django.conf.urls import patterns, url, include
from comicsite.admin import projectadminsite


urlpatterns = patterns('',

    url(r'^test/showData/$','comicsite.views.dataPage'),
    
    url(r'^test/sendEmail/$','comicsite.views.sendEmail'),
    
    url(r'^admin/$', include(projectadminsite.urls)),
                            
    url(r'^(?P<site_short_name>\w+)/$','comicsite.views.site'),
    
    url(r'^(?P<site_short_name>\w+)/files/$','comicmodels.views.upload_handler'),
    
    url(r'^(?P<site_short_name>\w+)/serve/(?P<filepath>.+)/$','comicsite.views.inserted_file'),
    
    url(r'^(?P<site_short_name>\w+)/_register/$','comicsite.views._register'),
    
    url(r'^(?P<site_short_name>\w+)/source/(?P<page_title>\w+)/$','comicsite.views.pagesource'),
    
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/db/(?P<dropboxname>\w+)/(?P<dropboxpath>.+)/$','comicsite.views.dropboxpage'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/insert/(?P<dropboxpath>.+)/$','comicsite.views.insertedpage'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),
    
)
    