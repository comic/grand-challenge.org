from django.urls import path

from grandchallenge.documentation.views import (
    DocPageDetail,
    DocPageList,
    DocumentationHome,
)

app_name = "documentation"

urlpatterns = [
    path("", DocumentationHome.as_view(), name="home"),
    path("overview/", DocPageList.as_view(), name="list"),
    path("<slug:slug>/", DocPageDetail.as_view(), name="detail"),
]
