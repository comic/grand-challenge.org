from django.urls import path

from grandchallenge.github.views import post_install_redirect

app_name = "github"

urlpatterns = [
    path(
        "github-install-complete/",
        post_install_redirect,
        name="github-install-complete",
    ),
]
