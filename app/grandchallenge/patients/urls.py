from django.urls import path
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    path('patients/', views.PatientTable.as_view(), name="patients"),
    path('patients/<int:pk>/', views.PatientRecord.as_view(), name="patient"),
    path('patients/list/', views.PatientList.as_view(), name="patient_list"),
    path('patients/create/', views.PatientCreate.as_view(), name="patient_create"),
    path('patients/update/<int:pk>/', views.PatientUpdate.as_view(), name="patient_update"),
    path('patients/delete/<int:pk>/', views.PatientDelete.as_view(), name="patient_delete"),
]
