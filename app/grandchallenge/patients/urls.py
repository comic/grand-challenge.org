from django.urls import path, re_path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path('patients/create/', views.PatientCreate.as_view(), name="patient_create"),
    path('patients/<int:pk>/update/', views.PatientUpdate.as_view(), name="patient_update"),
    path('patients/<int:pk>/delete/', views.PatientDelete.as_view(), name="patient_delete"),
    path('patients/', views.PatientTable.as_view(), name="patients"),
    re_path(r'^patients/(?P<pk>[0-9]+)$', views.PatientRecord.as_view(), name="patient"),
]
