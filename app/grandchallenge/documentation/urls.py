from django.urls import path

from grandchallenge.documentation.views import (
    DocPageCreate,
    DocPageDelete,
    DocPageDetail,
    DocPageList,
    DocPageUpdate,
    DocumentationHome,
)

app_name = "documentation"

urlpatterns = [
    path("", DocumentationHome.as_view(), name="home"),
    path("overview/", DocPageList.as_view(), name="list"),
    path("create/", DocPageCreate.as_view(), name="create"),
    path("<slug:slug>/", DocPageDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", DocPageUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", DocPageDelete.as_view(), name="delete"),
]
