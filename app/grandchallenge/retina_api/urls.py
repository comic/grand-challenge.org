from django.urls import path

from grandchallenge.retina_api import views

app_name = "retina_api"

urlpatterns = [
    path(
        "archive_data/",
        views.ArchiveAPIView.as_view(),
        name="archive-data-api-view",
    ),
    path(
        "archive_data/<uuid:pk>/",
        views.ArchiveAPIView.as_view(),
        name="archive-data-api-view",
    ),
    path(
        "image/thumbnail/<uuid:pk>/",
        views.B64ThumbnailAPIView.as_view(),
        name="image-thumbnail",
    ),
    path(
        "image/thumbnail/<uuid:pk>/<int:width>/<int:height>/",
        views.B64ThumbnailAPIView.as_view(),
        name="image-thumbnail",
    ),
]
