from django.urls import path

from grandchallenge.organizations.views import (
    OrganizationDetail,
    OrganizationList,
)

app_name = "organizations"

urlpatterns = [
    path("", OrganizationList.as_view(), name="list"),
    path("<slug>/", OrganizationDetail.as_view(), name="detail"),
]
