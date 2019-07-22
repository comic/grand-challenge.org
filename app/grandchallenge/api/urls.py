from django.conf.urls import include
from django.urls import path
from rest_framework_nested import routers

from grandchallenge.cases.views import ImageViewSet
from grandchallenge.patients.views import PatientViewSet
from grandchallenge.reader_studies.views import (
    ReaderStudyViewSet,
    QuestionViewSet,
    AnswerViewSet,
)
from grandchallenge.studies.views import StudyViewSet
from grandchallenge.worklists.views import WorklistViewSet
from grandchallenge.workstations.views import SessionViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")
router.register(r"studies", StudyViewSet, basename="study")
router.register(r"worklists", WorklistViewSet, basename="worklist")
router.register(r"cases/images", ImageViewSet, basename="image")
router.register(r"workstations/sessions", SessionViewSet)

# Nested router for /reader-studies/{reader_study_pk}/questions/{question_pk}/answers/
router.register(r"reader-studies", ReaderStudyViewSet, basename="reader-study")
reader_studies_router = routers.NestedDefaultRouter(
    router, r"reader-studies", lookup="reader_study"
)
reader_studies_router.register(
    r"questions", QuestionViewSet, base_name="reader-study-questions"
)
questions_router = routers.NestedDefaultRouter(
    reader_studies_router, r"questions", lookup="question"
)
questions_router.register(
    r"answers", AnswerViewSet, base_name="reader-study-question-answers"
)

urlpatterns = [
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    path("v1/", include(router.urls)),
    path("v1/", include(reader_studies_router.urls)),
    path("v1/", include(questions_router.urls)),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
]
