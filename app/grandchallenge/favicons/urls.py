from django.urls import path

from grandchallenge.favicons.views import FaviconView

app_name = "favicons"

urlpatterns = [
    path(
        "favicon.ico",
        FaviconView.as_view(rel="shortcut icon"),
        name="favicon",
    ),
    path(
        "apple-touch-icon.png",
        FaviconView.as_view(rel="apple-touch-icon"),
        name="apple-touch-icon",
    ),
    path(
        "apple-touch-icon-precomposed.png",
        FaviconView.as_view(rel="apple-touch-icon-precomposed"),
        name="apple-touch-icon-precomposed",
    ),
    path(
        "apple-touch-icon-<int:size>x<int>.png",
        FaviconView.as_view(rel="apple-touch-icon"),
        name="apple-touch-icon-sized",
    ),
    path(
        "apple-touch-icon-<int:size>x<int>-precomposed.png",
        FaviconView.as_view(rel="apple-touch-icon-precomposed"),
        name="apple-touch-icon-precomposed-sized",
    ),
]
