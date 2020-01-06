from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from grandchallenge.algorithms.views import (
    AlgorithmImageViewSet,
    AlgorithmViewSet,
    JobViewSet,
    ResultViewSet,
)
from grandchallenge.cases.views import (
    ImageViewSet,
    RawImageFileViewSet,
    RawImageUploadSessionViewSet,
)
from grandchallenge.jqfileupload.views import StagedFileViewSet
from grandchallenge.reader_studies.views import (
    AnswerViewSet,
    QuestionViewSet,
    ReaderStudyViewSet,
)
from grandchallenge.retina_api.views import LandmarkAnnotationSetViewSet
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.workstation_configs.views import WorkstationConfigViewSet
from grandchallenge.workstations.views import SessionViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(
    r"cases/upload-sessions",
    RawImageUploadSessionViewSet,
    basename="upload-session",
)
router.register(
    r"cases/image-files", RawImageFileViewSet, basename="image-file"
)
router.register(r"cases/images", ImageViewSet, basename="image")
router.register(r"workstations/sessions", SessionViewSet)
router.register(
    r"workstations/configs",
    WorkstationConfigViewSet,
    basename="workstations-config",
)
router.register(r"algorithms/jobs", JobViewSet, basename="algorithms-job")
router.register(
    r"algorithms/results", ResultViewSet, basename="algorithms-result"
)
router.register(
    r"algorithms/images", AlgorithmImageViewSet, basename="algorithms-image"
)
router.register(r"algorithms", AlgorithmViewSet, basename="algorithm")

router.register(
    r"reader-studies/answers", AnswerViewSet, basename="reader-studies-answer"
)
router.register(
    r"reader-studies/questions",
    QuestionViewSet,
    basename="reader-studies-question",
)
router.register(r"reader-studies", ReaderStudyViewSet, basename="reader-study")
router.register(r"chunked-uploads", StagedFileViewSet, basename="staged-file")

router.register(
    r"retina/landmark-annotation",
    LandmarkAnnotationSetViewSet,
    basename="landmark-annotation",
)

# TODO: add terms_of_service and contact
schema_view = get_schema_view(
    openapi.Info(
        title=f"{settings.SESSION_COOKIE_DOMAIN.lstrip('.')} API",
        default_version="v1",
        description=f"The API for {settings.SESSION_COOKIE_DOMAIN.lstrip('.')}.",
        license=openapi.License(name="Apache License 2.0"),
        terms_of_service=reverse_lazy(
            "policies:detail", kwargs={"slug": "terms-of-service"}
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[path("api/v1/", include(router.urls))],
)

urlpatterns = [
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(),
        name="schema-json",
    ),
    # Do not namespace the router.urls without updating the view names in
    # the serializers
    path("v1/", include(router.urls)),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("", schema_view.with_ui("swagger"), name="schema-docs"),
]
