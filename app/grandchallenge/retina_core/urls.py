from django.urls import include, path

from grandchallenge.retina_core.views import (
    IndexView,
    NumpyView,
    ThumbnailView,
)

app_name = "retina"
urlpatterns = [
    path("", IndexView.as_view(), name="home"),
    path("api/", include("grandchallenge.retina_api.urls", namespace="api")),
    path(
        "retina_importers/",
        include("grandchallenge.retina_importers.urls", namespace="importers"),
    ),
    path(
        "image/thumbnail/<uuid:image_id>/",
        ThumbnailView.as_view(),
        name="image-thumbnail",
    ),
    path(
        "image/numpy/<uuid:image_id>/",
        NumpyView.as_view(),
        name="image-numpy",
    ),
]
