from django.conf import settings
from django.urls import path

from grandchallenge.serving.views import (
    serve_images,
    serve_submissions,
)

app_name = "serving"

urlpatterns = [
    path(
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/<uuid:pk>/<path:path>",
        serve_images,
    ),
    path(
        (
            f"{settings.EVALUATION_FILES_SUBDIRECTORY}/"
            f"<int:challenge_pk>/"
            f"submissions/"
            f"<int:creator_pk>/"
            f"<uuid:submission_pk>/"
            f"<path:path>"
        ),
        serve_submissions,
    ),
]
