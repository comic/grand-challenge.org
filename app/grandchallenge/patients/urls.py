from django.urls import path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path("patient/", views.PatientTable.as_view(), name="patients"),
    path("patient/<uuid:pk>/", views.PatientRecord.as_view(), name="patient"),
    path(
        "patient/create/",
        views.PatientCreateView.as_view(),
        name="patient-create",
    ),
    path(
        "patient/remove/<uuid:pk>/",
        views.PatientRemoveView.as_view(),
        name="patient-remove",
    ),
    path(
        "patient/update/<uuid:pk>/",
        views.PatientUpdateView.as_view(),
        name="patient-update",
    ),
    path(
        "patient/display/",
        views.PatientDisplayView.as_view(),
        name="patient-display",
    ),
]
