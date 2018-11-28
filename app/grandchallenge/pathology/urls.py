from django.urls import path
from grandchallenge.pathology import views

app_name = "pathology"
urlpatterns = [
    path("pathology/patient_items/", views.PatientItemTable.as_view(), name="patient-items"),
    path("pathology/patient_items/<uuid:pk>/", views.PatientItemRecord.as_view(), name="patient-item"),
    path("pathology/patient_items/create/", views.PatientItemCreateView.as_view(), name="patient-item-create"),
    path("pathology/patient_items/remove/", views.PatientItemRemoveView.as_view(), name="patient-item-remove"),
    path("pathology/patient_items/update/", views.PatientItemUpdateView.as_view(), name="patient-item-update"),
    path("pathology/patient_items/display/", views.PatientItemDisplayView.as_view(), name="patient-item-display"),
    path("pathology/study_items/", views.StudyItemTable.as_view(), name="study-items"),
    path("pathology/study_items/<uuid:pk>/", views.StudyItemRecord.as_view(), name="study-item"),
    path("pathology/study_items/create/", views.StudyItemCreateView.as_view(), name="study-item-create"),
    path("pathology/study_items/remove/", views.StudyItemRemoveView.as_view(), name="study-item-remove"),
    path("pathology/study_items/update/", views.StudyItemUpdateView.as_view(), name="study-item-update"),
    path("pathology/study_items/display/", views.StudyItemDisplayView.as_view(), name="study-item-display"),
    path("pathology/worklist_items/", views.WorklistItemTable.as_view(), name="worklist-items"),
    path("pathology/worklist_items/<uuid:pk>/", views.WorklistItemRecord.as_view(), name="worklist-item"),
    path("pathology/worklist_items/create/", views.WorklistItemCreateView.as_view(), name="worklist-item-create"),
    path("pathology/worklist_items/remove/", views.WorklistItemRemoveView.as_view(), name="worklist-item-remove"),
    path("pathology/worklist_items/update/", views.WorklistItemUpdateView.as_view(), name="worklist-item-update"),
    path("pathology/worklist_items/display/", views.WorklistItemDisplayView.as_view(), name="worklist-item-display"),
]
