from django.urls import path
from grandchallenge.patients.views_forms import (
    PatientListView,
    PatientCreateView,
    PatientDetailView,
    PatientUpdateView,
    PatientDeleteView,
)

app_name = "patients"
urlpatterns = [
    path("", PatientListView.as_view(), name="list"),
    path("create/", PatientCreateView.as_view(), name="create"),
    path("<uuid:pk>/detail/", PatientDetailView.as_view(), name="detail"),
    path("<uuid:pk>/update/", PatientUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", PatientDeleteView.as_view(), name="delete"),
]
