from django.urls import path

from grandchallenge.cases.views import (
    RawImageUploadSessionDetail,
    show_image,
)

app_name = "cases"

urlpatterns = [
    path(
        "uploads/<uuid:pk>/",
        RawImageUploadSessionDetail.as_view(),
        name="raw-files-session-detail",
    ),
    path("uploads/show_image/<uuid:pk>/", show_image, name="show_image"),
]
