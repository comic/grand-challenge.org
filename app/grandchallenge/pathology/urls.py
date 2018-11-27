from django.urls import path, re_path
from grandchallenge.pathology import views

app_name = "pathology"
urlpatterns = [
    path("pathology/worklist_items/", views.WorklistItemTable.as_view(), name="worklist-items"),
    path("pathology/worklist_items/<uuid:pk>/", views.WorklistItemRecord.as_view(), name="worklist-item"),
    path("pathology/patient_items/", views.PatientItemTable.as_view(), name="patient-items"),
    path("pathology/patient_items/<uuid:pk>/", views.PatientItemRecord.as_view(), name="patient-item"),
    path("pathology/patient_items/create/", views.PatientItemCreateView.as_view(), name="patient-item-create"),
    path("pathology/study_items/", views.StudyItemTable.as_view(), name="study-items"),
    path("pathology/study_items/<uuid:pk>/", views.StudyItemRecord.as_view(), name="study-item"),
]
