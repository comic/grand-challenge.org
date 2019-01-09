from django.urls import path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path("", views.PatientTable.as_view(), name="patients"),
    path("<uuid:pk>/", views.PatientRecord.as_view(), name="patient"),
    path("create/", views.PatientCreateView.as_view(), name="patient-create"),
    path("remove/<uuid:pk>/", views.PatientRemoveView.as_view(), name="patient-remove"),
    path("update/<uuid:pk>/", views.PatientUpdateView.as_view(), name="patient-update"),
    path("display/", views.PatientDisplayView.as_view(), name="patient-display"),
]
