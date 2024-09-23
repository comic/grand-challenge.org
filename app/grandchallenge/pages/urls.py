from django.urls import path

from grandchallenge.pages.views import (
    ChallengeHome,
    ChallengeStatistics,
    PageCreate,
    PageDelete,
    PageDetail,
    PageList,
    PagePandoc,
    PageUpdate,
)

app_name = "pages"

urlpatterns = [
    path("pages/", PageList.as_view(), name="list"),
    path("pages/create/", PageCreate.as_view(), name="create"),
    path("statistics/", ChallengeStatistics.as_view(), name="statistics"),
    path("", ChallengeHome.as_view(), name="home"),
    path("<slug>/", PageDetail.as_view(), name="detail"),
    path("<slug>/update/", PageUpdate.as_view(), name="update"),
    path("<slug>/delete/", PageDelete.as_view(), name="delete"),
    path(
        "<slug>/pandoc/<str:format>/",
        PagePandoc.as_view(raw=False),
        name="detail-pandoc",
    ),
    path(
        "<slug>/pandoc/<str:format>/raw/",
        PagePandoc.as_view(raw=True),
        name="detail-pandoc-raw",
    ),
]
