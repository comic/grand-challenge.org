from django.conf import settings
from django.urls import path

from grandchallenge.serving.views import (
    serve_folder,
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
    path("logos/<path:path>", serve_folder, {"folder": "logos"}),
    path("banners/<path:path>", serve_folder, {"folder": "banners"}),
    path("mugshots/<path:path>", serve_folder, {"folder": "mugshots"}),
    path("favicon/<path:path>", serve_folder, {"folder": "favicon"}),
    path("i/<path:path>", serve_folder, {"folder": "i"}),
    path("cache/<path:path>", serve_folder, {"folder": "cache"}),
    path(
        "evaluation-supplementary/<path:path>",
        serve_folder,
        {"folder": "evaluation-supplementary"},
    ),
    path(
        "<slug:challenge_name>/<path:path>",
        serve_folder,
        name="challenge-file",
    ),
]
