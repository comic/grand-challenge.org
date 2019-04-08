from django.urls import path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path("patient/", views.PatientTable.as_view(), name="patients"),
    path("patient/<uuid:pk>/", views.PatientRecord.as_view(), name="patient"),
    path("", views.PatientListView.as_view(), name="list"),
    path("create/", views.PatientCreateView.as_view(), name="create"),
    path(
        "<uuid:pk>/update/", views.PatientUpdateView.as_view(), name="update"
    ),
    path(
        "<uuid:pk>/delete/", views.PatientDeleteView.as_view(), name="delete"
    ),
]
