from django.urls import path
from grandchallenge.studies.views_forms import (
    StudyListView,
    StudyCreateView,
    StudyDetailView,
    StudyUpdateView,
    StudyDeleteView,
)

app_name = "studies"
urlpatterns = [
    path("", StudyListView.as_view(), name="list"),
    path("create/", StudyCreateView.as_view(), name="create"),
    path("<uuid:pk>/detail/", StudyDetailView.as_view(), name="detail"),
    path("<uuid:pk>/delete/", StudyDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/update/", StudyUpdateView.as_view(), name="update"),
]
