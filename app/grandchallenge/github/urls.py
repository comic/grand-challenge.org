from django.urls import path

from grandchallenge.github.views import RepositoriesList, post_install_redirect

app_name = "github"

urlpatterns = [
    path("install-complete/", post_install_redirect, name="install-complete"),
    path(
        "repositories/", RepositoriesList.as_view(), name="repositories-list"
    ),
]
