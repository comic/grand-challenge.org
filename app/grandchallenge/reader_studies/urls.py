from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget
from grandchallenge.reader_studies.views import (
    AddImagesToReaderStudy,
    AddQuestionToReaderStudy,
    EditorsUpdate,
    ReaderStudyCreate,
    ReaderStudyDetail,
    ReaderStudyList,
    ReaderStudyUpdate,
    ReaderStudyUserAutocomplete,
    ReadersUpdate,
)

app_name = "reader-studies"

urlpatterns = [
    path("", ReaderStudyList.as_view(), name="list"),
    path("create/", ReaderStudyCreate.as_view(), name="create"),
    path(
        "users-autocomplete/",
        ReaderStudyUserAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    path("<slug>/", ReaderStudyDetail.as_view(), name="detail"),
    path("<slug>/update/", ReaderStudyUpdate.as_view(), name="update"),
    path(
        "<slug>/images/add/",
        AddImagesToReaderStudy.as_view(),
        name="add-images",
    ),
    path(
        f"<slug>/images/add/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-readerstudy-image-files-ajax",
    ),
    path(
        "<slug>/questions/add/",
        AddQuestionToReaderStudy.as_view(),
        name="add-question",
    ),
    path(
        "<slug>/editors/update/",
        EditorsUpdate.as_view(),
        name="editors-update",
    ),
    path(
        "<slug>/readers/update/",
        ReadersUpdate.as_view(),
        name="readers-update",
    ),
]
