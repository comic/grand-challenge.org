from django.conf.urls import include, url

from profiles.forms import SignupFormExtra
from profiles.views import login_redirect, profile_edit, profile, signup, \
    signup_complete

urlpatterns = [
    url(r'^signup/$', signup, {'signup_form': SignupFormExtra},
        name="profile_signup"),
    url(r'^signup_complete/$', signup_complete,
        name="profile_signup_complete"),
    url(r'^login-redirect/$', login_redirect, name='login_redirect'),
    url(r'^profile/edit/$', profile_edit, name='profile_redirect_edit'),
    url(r'^profile/$', profile, name='profile_redirect'),
    url(r'^', include('userena.urls')),
]
