from django.conf.urls import include
from django.urls import path
from rest_framework import routers

from grandchallenge.algorithms.views import (
    AlgorithmImageViewSet,
    AlgorithmViewSet,
    JobViewSet,
    ResultViewSet,
)
from grandchallenge.cases.views import (
    ImageViewSet,
    RawImageUploadSessionViewSet,
)
from grandchallenge.jqfileupload.views import StagedFileViewSet
from grandchallenge.patients.views import PatientViewSet
from grandchallenge.reader_studies.views import (
    AnswerViewSet,
    QuestionViewSet,
    ReaderStudyViewSet,
)
from grandchallenge.studies.views import StudyViewSet
from grandchallenge.worklists.views import WorklistViewSet
from grandchallenge.workstation_configs.views import WorkstationConfigViewSet
from grandchallenge.workstations.views import SessionViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")
router.register(r"studies", StudyViewSet, basename="study")
router.register(r"worklists", WorklistViewSet, basename="worklist")
router.register(
    r"cases/upload-sessions",
    RawImageUploadSessionViewSet,
    basename="upload-session",
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


urlpatterns = [
    # Do not namespace the router.urls without updating the view names in
    # the serializers
    path("v1/", include(router.urls)),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
]
