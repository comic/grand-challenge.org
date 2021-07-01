from django.urls import path

from grandchallenge.github.views import post_install_redirect

app_name = "github"

urlpatterns = [
    path("install-complete/", post_install_redirect, name="install-complete"),
]
