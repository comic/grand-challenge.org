from django.urls import path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path('patients/&', views.PatientTable.as_view(), name="patients"),
    path('patients/(?P<pk>[0-9]+)$', views.PatientRecord.as_view(), name="patient")
]
