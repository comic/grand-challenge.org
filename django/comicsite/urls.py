from django.conf.urls import patterns, url


urlpatterns = patterns('',

    url(r'^test/showData/$','comicsite.views.dataPage'),
    
    url(r'^test/sendEmail/$','comicsite.views.sendEmail'),
                            
    url(r'^(?P<site_short_name>\w+)/$','comicsite.views.site'),
    
    url(r'^(?P<site_short_name>\w+)/files/$','comicmodels.views.upload_handler'),
    
    url(r'^(?P<site_short_name>\w+)/_register/$','comicsite.views._register'),
    
    url(r'^(?P<site_short_name>\w+)/source/(?P<page_title>\w+)/$','comicsite.views.pagesource'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),
    
    
        
    
    
    
)
    