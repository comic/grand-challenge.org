from django.urls import path
from grandchallenge.patients.views_forms import (
    PatientList,
    PatientCreate,
    PatientDetail,
    PatientUpdate,
    PatientDelete,
)

app_name = "patients"
urlpatterns = [
    path("", PatientList.as_view(), name="list"),
    path("create/", PatientCreate.as_view(), name="create"),
    path("<uuid:pk>/detail/", PatientDetail.as_view(), name="detail"),
    path("<uuid:pk>/update/", PatientUpdate.as_view(), name="update"),
    path("<uuid:pk>/delete/", PatientDelete.as_view(), name="delete"),
]
