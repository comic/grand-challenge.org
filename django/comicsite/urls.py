from django.conf.urls import patterns, url


urlpatterns = patterns('',

    
    url(r'^newsite/$','comicsite.views.newsite'),
                    
    url(r'^(?P<site_short_name>\w+)/$','comicsite.views.site'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),

    url(r'^test/showData/$','comicsite.views.dataPage'),
    
    
)
    