from django.urls import path

from grandchallenge.pages.views import (
    page,
    insertedpage,
    PageList,
    PageCreate,
    PageUpdate,
    PageDelete,
    FaviconView,
)

app_name = "pages"

urlpatterns = [
    path("pages/", PageList.as_view(), name="list"),
    path("pages/create/", PageCreate.as_view(), name="create"),
    # Favicons
    path(
        "favicon.ico/",
        FaviconView.as_view(rel="shortcut icon"),
        name="favicon",
    ),
    path(
        "apple-touch-icon.png/",
        FaviconView.as_view(rel="apple-touch-icon"),
        name="apple-touch-icon",
    ),
    path(
        "apple-touch-icon-precomposed.png/",
        FaviconView.as_view(rel="apple-touch-icon-precomposed"),
        name="apple-touch-icon-precomposed",
    ),
    path(
        "apple-touch-icon-<int:size>x<int>.png/",
        FaviconView.as_view(rel="apple-touch-icon"),
        name="apple-touch-icon-sized",
    ),
    path(
        "apple-touch-icon-<int:size>x<int>-precomposed.png/",
        FaviconView.as_view(rel="apple-touch-icon-precomposed"),
        name="apple-touch-icon-precomposed-sized",
    ),
    path("<slug:page_title>/", page, name="detail"),
    path("<slug:page_title>/update/", PageUpdate.as_view(), name="update"),
    path("<slug:page_title>/delete/", PageDelete.as_view(), name="delete"),
    path(
        "<slug:page_title>/insert/<path:dropboxpath>/",
        insertedpage,
        name="insert-detail",
    ),
]
