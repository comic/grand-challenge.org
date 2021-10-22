from django.urls import path

from grandchallenge.retina_api import views

app_name = "retina_api"

urlpatterns = [
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
