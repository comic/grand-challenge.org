from django.urls import path

from grandchallenge.pages.views import (
    ChallengeHome,
    PageCreate,
    PageDelete,
    PageDetail,
    PageList,
    PageUpdate,
)

app_name = "pages"

urlpatterns = [
    path("pages/", PageList.as_view(), name="list"),
    path("pages/create/", PageCreate.as_view(), name="create"),
    path("", ChallengeHome.as_view(), name="home"),
    path("<slug:page_title>/", PageDetail.as_view(), name="detail"),
    path("<slug:page_title>/update/", PageUpdate.as_view(), name="update"),
    path("<slug:page_title>/delete/", PageDelete.as_view(), name="delete"),
]
