from django.urls import path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path("patients/", views.PatientTable.as_view(), name="patients"),
    path("patients/<uuid:pk>/", views.PatientRecord.as_view(), name="patient"),
    path("patients/create/", views.PatientCreateView.as_view(), name="patient-create"),
    path("patients/remove/<uuid:pk>/", views.PatientRemoveView.as_view(), name="patient-remove"),
    path("patients/update/<uuid:pk>/", views.PatientUpdateView.as_view(), name="patient-update"),
    path("patients/display/", views.PatientDisplayView.as_view(), name="patient-display"),
]
