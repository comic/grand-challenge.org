from django.urls import path

from grandchallenge.participants.views import (
    ParticipantsList,
    RegistrationQuestionCreate,
    RegistrationQuestionList,
    RegistrationRequestCreate,
    RegistrationRequestList,
    RegistrationRequestUpdate,
)

app_name = "participants"

urlpatterns = [
    path("", ParticipantsList.as_view(), name="list"),
    path(
        "registration/",
        RegistrationRequestList.as_view(),
        name="registration-list",
    ),
    path(
        "registration/create/",
        RegistrationRequestCreate.as_view(),
        name="registration-create",
    ),
    path(
        "registration/<int:pk>/update/",
        RegistrationRequestUpdate.as_view(),
        name="registration-update",
    ),
    path(
        "registration/questions/",
        RegistrationQuestionList.as_view(),
        name="registration-question-list",
    ),
    path(
        "registration/questions/create",
        RegistrationQuestionCreate.as_view(),
        name="registration-question-create",
    ),
]
