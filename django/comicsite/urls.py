from django.conf.urls import patterns, url, include
from comicsite.admin import projectadminsite
from profiles.forms import SignupFormExtra

urlpatterns = patterns('',

    url(r'^test/showData/$','comicsite.views.dataPage'),
    
    url(r'^test/sendEmail/$','comicsite.views.sendEmail'),
    
    #url(r'^admin/', include(projectadminsite.urls)),
                             
    url(r'^(?P<site_short_name>\w+)/$','comicsite.views.site'),
    
    url(r'^(?P<site_short_name>\w+)/admin/', include(projectadminsite.urls)),
    
    # these registration and account views are viewed in the context of a
    # project
    url(r'^(?P<site_short_name>\w+)/accounts/signin/$','comicsite.views.signin',name="comicsite_signin"),
    url(r'^(?P<site_short_name>\w+)/accounts/signup/$','comicsite.views.signup',{'signup_form':SignupFormExtra},name="comicsite_signup"),    
    url(r'^(?P<site_short_name>\w+)/accounts/signup_complete/$','comicsite.views.signup_complete',name="comicsite_signup_complete"),
#    url(r'^(?P<site_short_name>\w+)/accounts/signup/$','comicsite.views.signup',{'signup_form':SignupFormExtra},name="comicsite_signup"),
    
    #url(r'^(?P<site_short_name>\w+)/',include('social_auth.urls')),
        
          
    
            
    url(r'^(?P<site_short_name>\w+)/files/$','comicmodels.views.upload_handler'),
    
    url(r'^(?P<project_name>\w+)/serve/(?P<path>.+)/$','filetransfers.views.serve',name="project_serve_file"),
    
    url(r'^(?P<site_short_name>\w+)/_register/$','comicsite.views._register'),
    
    url(r'^(?P<site_short_name>\w+)/source/(?P<page_title>\w+)/$','comicsite.views.pagesource'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/db/(?P<dropboxname>\w+)/(?P<dropboxpath>.+)/$','comicsite.views.dropboxpage'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/insert/(?P<dropboxpath>.+)/$','comicsite.views.insertedpage'),
    
    url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),
    
)
    