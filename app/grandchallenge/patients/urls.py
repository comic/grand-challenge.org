from django.urls import path, re_path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path('patients/', views.PatientTable.as_view(), name="patients"),
    path(r'^patients/<pk>/$', views.PatientRecord.as_view(), name="patient"),
    path('patients/create/', views.PatientCreate.as_view(), name="patient_create"),
    path(r'^patients/update/<pk>/$', views.PatientUpdate.as_view(), name="patient_update"),
    path(r'^patients/delete/<pk>/$', views.PatientDelete.as_view(), name="patient_delete"),
]
