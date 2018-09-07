from django.urls import path

from grandchallenge.admins.views import AdminsList, AdminsUpdate

app_name = "admins"

urlpatterns = [
    path("", AdminsList.as_view(), name="list"),
    path("update/", AdminsUpdate.as_view(), name="update"),
]
