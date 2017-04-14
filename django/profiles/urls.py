from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    #url(r'^signup/$','userena.views.signup',{'signup_form':SignupFormExtra}),    
    url(r'^profile/edit/','profiles.views.profile_edit', name='profile_redirect_edit'),
    url(r'^profile/','profiles.views.profile', name='profile_redirect'),
    url(r'^',include('userena.urls')),
)
