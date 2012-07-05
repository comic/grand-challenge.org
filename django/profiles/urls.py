from django.conf.urls import patterns, include, url

from profiles.forms import SignupFormExtra


urlpatterns = patterns('',
    url(r'^signup/$','userena.views.signup',{'signup_form':SignupFormExtra}),
    url(r'^',include('userena.urls')),

    # requirement for social_auth
    #url(r'',include('social_auth.urls')),
)
    
