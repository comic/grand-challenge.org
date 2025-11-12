from django.conf import settings
from django.urls import path, register_converter
from django.urls.converters import get_converters

from grandchallenge.serving.views import (
    serve_algorithm_images,
    serve_algorithm_models,
    serve_component_interface_value,
    serve_images,
    serve_session_feedback_screenshot,
    serve_structured_challenge_submission_form,
    serve_submission_supplementary_file,
    serve_submissions,
)

app_name = "serving"


class PrefixConverter:
    regex = r"[0-9a-fA-F]{2}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)


if "prefix" not in get_converters():
    register_converter(PrefixConverter, "prefix")

urlpatterns = [
    path(
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/<uuid:pk>/<path:path>",
        serve_images,
    ),
    path(
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/<prefix:pa>/<prefix:pb>/<uuid:pk>/<path:path>",
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
            f"{settings.EVALUATION_SUPPLEMENTARY_FILES_SUBDIRECTORY}/"
            f"<int:challenge_pk>/"
            f"<uuid:submission_pk>/"
            f"<path:path>"
        ),
        serve_submission_supplementary_file,
    ),
    path(
        (
            f"{settings.COMPONENTS_FILES_SUBDIRECTORY}/"
            f"componentinterfacevalue/"
            f"<prefix:pa>/"
            f"<prefix:pb>/"
            f"<int:component_interface_value_pk>/"
            f"<path:path>"
        ),
        serve_component_interface_value,
    ),
    path(
        (
            "challenges/"
            "challengerequest/"
            "<uuid:challenge_request_pk>/"
            "<path:path>"
        ),
        serve_structured_challenge_submission_form,
    ),
    path(
        (
            "docker/"
            "images/"
            "algorithms/"
            "algorithmimage/"
            "<uuid:algorithmimage_pk>/"
            "<path:path>"
        ),
        serve_algorithm_images,
    ),
    path(
        (
            "models/"
            "algorithms/"
            "algorithmmodel/"
            "<uuid:algorithmmodel_pk>/"
            "<path:path>"
        ),
        serve_algorithm_models,
    ),
    path(
        "session-feedback/<uuid:feedback_pk>/<path:path>",
        serve_session_feedback_screenshot,
    ),
]
