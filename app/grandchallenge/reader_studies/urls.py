from django.urls import path

from grandchallenge.reader_studies.views import (
    ReaderStudyList,
    ReaderStudyCreate,
    ReaderStudyDetail,
)

app_name = "reader-studies"

urlpatterns = [
    path("", ReaderStudyList.as_view(), name="list"),
    path("create/", ReaderStudyCreate.as_view(), name="create"),
    path("<slug>/", ReaderStudyDetail.as_view(), name="detail"),
]
