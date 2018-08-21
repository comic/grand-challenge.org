from django.conf.urls import url

from grandchallenge.admins.views import AdminsList, AdminsUpdate

app_name = "admins"

urlpatterns = [
    url(r"^$", AdminsList.as_view(), name="list"),
    url(r"^update/$", AdminsUpdate.as_view(), name="update"),
]
