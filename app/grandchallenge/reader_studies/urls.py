from django.urls import path

from grandchallenge.reader_studies.views import (
    AddGroundTruthToReaderStudy,
    AddImagesToReaderStudy,
    AddQuestionToReaderStudy,
    AnswersRemove,
    EditorsUpdate,
    QuestionUpdate,
    ReaderStudyCopy,
    ReaderStudyCreate,
    ReaderStudyDelete,
    ReaderStudyDetail,
    ReaderStudyExampleGroundTruth,
    ReaderStudyImages,
    ReaderStudyLeaderBoard,
    ReaderStudyList,
    ReaderStudyPermissionRequestCreate,
    ReaderStudyPermissionRequestList,
    ReaderStudyPermissionRequestUpdate,
    ReaderStudyStatistics,
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
    path("<slug>/delete/", ReaderStudyDelete.as_view(), name="delete"),
    path(
        "<slug>/leaderboard/",
        ReaderStudyLeaderBoard.as_view(),
        name="leaderboard",
    ),
    path("<slug>/images/", ReaderStudyImages.as_view(), name="images",),
    path(
        "<slug>/statistics/",
        ReaderStudyStatistics.as_view(),
        name="statistics",
    ),
    path("<slug>/copy/", ReaderStudyCopy.as_view(), name="copy",),
    path(
        "<slug>/remove-answers/",
        AnswersRemove.as_view(),
        name="answers-remove",
    ),
    path(
        "<slug>/ground-truth/add/",
        AddGroundTruthToReaderStudy.as_view(),
        name="add-ground-truth",
    ),
    path(
        "<slug>/ground-truth/example/",
        ReaderStudyExampleGroundTruth.as_view(),
        name="example-ground-truth",
    ),
    path(
        "<slug>/images/add/",
        AddImagesToReaderStudy.as_view(),
        name="add-images",
    ),
    path(
        "<slug>/questions/add/",
        AddQuestionToReaderStudy.as_view(),
        name="add-question",
    ),
    path(
        "<slug>/questions/<pk>/update/",
        QuestionUpdate.as_view(),
        name="question-update",
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
    path(
        "<slug>/permission-requests/",
        ReaderStudyPermissionRequestList.as_view(),
        name="permission-request-list",
    ),
    path(
        "<slug>/permission-requests/create/",
        ReaderStudyPermissionRequestCreate.as_view(),
        name="permission-request-create",
    ),
    path(
        "<slug>/permission-requests/<int:pk>/update/",
        ReaderStudyPermissionRequestUpdate.as_view(),
        name="permission-request-update",
    ),
]
