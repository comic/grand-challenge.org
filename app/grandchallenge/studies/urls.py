from django.urls import path
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    path("study/", views.StudyTable.as_view(), name="studies"),
    path("study/<uuid:pk>/", views.StudyRecord.as_view(), name="study"),
    path(
        "study/create/", views.StudyCreateView.as_view(), name="study-create"
    ),
    path(
        "study/remove/<uuid:pk>/",
        views.StudyRemoveView.as_view(),
        name="study-remove",
    ),
    path(
        "study/update/<uuid:pk>/",
        views.StudyUpdateView.as_view(),
        name="study-update",
    ),
    path(
        "study/display/",
        views.StudyDisplayView.as_view(),
        name="study-display",
    ),
]
