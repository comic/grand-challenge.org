from django.conf.urls import patterns, include, url
from django.views.generic import ListView
from django.contrib import admin
from comicsite.models import ComicSite
from django.views.generic.simple import redirect_to 

admin.autodiscover()

urlpatterns = patterns('',
    
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # for convenience in developing: redirect to not have to type /comic 
    # after 'localhost' to load site for the first time
    #(r'^$', redirect_to, {'url': '/'+urlPrefix}),
     
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    
    # main page 
    url(r'^$',ListView.as_view(model=ComicSite, template_name='index.html'),name = 'home'),
    
    #specific view of single comicsite
    url(r'^site/(?P<site_name>\w+)/$','comicsite.views.site'),
    
    url(r'^site/(?P<site_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),
    
    
    url(r'^test/showData/$','comicsite.views.dataPage'),
    
    # requirement for social_auth
    url(r'',include('social_auth.urls')),
)
    
