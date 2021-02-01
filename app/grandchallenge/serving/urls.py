from django.conf import settings
from django.urls import path, register_converter

from grandchallenge.serving.views import (
    serve_component_interface_value,
    serve_images,
    serve_submissions,
)

app_name = "serving"


class UUIDPrefixConverter:
    regex = r"[0-9a-fA-F]{2}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)


register_converter(UUIDPrefixConverter, "uuidprefix")

urlpatterns = [
    path(
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/<uuid:pk>/<path:path>",
        serve_images,
    ),
    path(
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/<uuidprefix:pa>/<uuidprefix:pb>/<uuid:pk>/<path:path>",
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
    path(
        (
            f"{settings.COMPONENTS_FILES_SUBDIRECTORY}/"
            f"componentinterfacevalue/"
            f"<uuidprefix:pa>/"
            f"<uuidprefix:pb>/"
            f"<int:component_interface_value_pk>/"
            f"<path:path>"
        ),
        serve_component_interface_value,
    ),
]
