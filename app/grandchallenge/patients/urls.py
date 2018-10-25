from django.urls import path, re_path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path('patients/', views.PatientTable.as_view(), name="patients_table"),
  #  re_path(r'^patients/(?P<pk>[0-9]+)$', views.PatientRecord.as_view(), name="patient")
]
