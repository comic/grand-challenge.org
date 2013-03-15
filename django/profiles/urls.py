from django.conf.urls import patterns, include, url

from profiles.forms import SignupFormExtra


urlpatterns = patterns('',
    url(r'^signup/$','userena.views.signup',{'signup_form':SignupFormExtra}),
    url(r'^profile/','profiles.views.profile', name='profile_redirect'),
    url(r'^',include('userena.urls')),
    
)
    
