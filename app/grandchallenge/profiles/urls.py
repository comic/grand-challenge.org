from django.conf.urls import include, url

from grandchallenge.profiles.forms import SignupFormExtra
from grandchallenge.profiles.views import (
    login_redirect,
    profile_edit_redirect,
    profile,
    signup,
    signup_complete,
    profile_edit,
)

urlpatterns = [
    url(
        r"^signup/$",
        signup,
        {"signup_form": SignupFormExtra},
        name="profile_signup",
    ),
    url(r"^signup_complete/$", signup_complete, name="profile_signup_complete"),
    url(r"^login-redirect/$", login_redirect, name="login_redirect"),
    url(
        r"^profile/edit/$", profile_edit_redirect, name="profile_redirect_edit"
    ),
    url(r"^profile/$", profile, name="profile_redirect"),
    url(
        r"^(?P<username>[\@\.\+\w-]+)/edit/$",
        profile_edit,
        name="userena_profile_edit",
    ),
    url(r"^", include("userena.urls")),
]
