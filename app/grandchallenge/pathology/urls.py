from django.urls import path, re_path
from grandchallenge.pathology import views

app_name = "pathology"
urlpatterns = [
    path("pathology/worklist_items/", views.WorklistItemsTable.as_view(), name="worklist-items"),
    path("pathology/worklist_items/<uuid:pk>", views.WorklistItemsRecord.as_view(), name="worklist-item"),
    path("pathology/patient_items/", views.PatientItemsTable.as_view(), name="patient-items"),
    path("pathology/patient_items/<uuid:pk>", views.PatientItemsRecord.as_view(), name="patient-item"),
    path("pathology/study_items/", views.StudyItemsTable.as_view(), name="study-items"),
    path("pathology/study_items/<uuid:pk>", views.StudyItemsRecord.as_view(), name="study-item"),
]
