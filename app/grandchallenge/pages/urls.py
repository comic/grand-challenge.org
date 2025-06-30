from django.urls import path

from grandchallenge.pages.views import (
    ChallengeHome,
    ChallengeStatistics,
    PageContentUpdate,
    PageCreate,
    PageDelete,
    PageDetail,
    PageList,
    PageMetadataUpdate,
)

app_name = "pages"

urlpatterns = [
    path("pages/", PageList.as_view(), name="list"),
    path("pages/create/", PageCreate.as_view(), name="create"),
    path("statistics/", ChallengeStatistics.as_view(), name="statistics"),
    path("", ChallengeHome.as_view(), name="home"),
    path("pages/<slug>/", PageDetail.as_view(), name="detail"),
    path(
        "pages/<slug>/content-update/",
        PageContentUpdate.as_view(),
        name="content-update",
    ),
    path(
        "pages/<slug>/metadata-update/",
        PageMetadataUpdate.as_view(),
        name="metadata-update",
    ),
    path("pages/<slug>/delete/", PageDelete.as_view(), name="delete"),
]
