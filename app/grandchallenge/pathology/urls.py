from django.urls import path, re_path
from grandchallenge.pathology import views

app_name = "pathology"
urlpatterns = [
    path("worklist_items/", views.WorklistItemsTable.as_view(), name="worklist_items"),
    path("worklist_items/<uuid:pk>", views.WorklistItemsRecord.as_view(), name="worklist_item"),
    path("patient_items/", views.PatientItemsTable.as_view(), name="patient_items"),
    path("patient_items/<uuid:pk>", views.PatientItemsRecord.as_view(), name="patient_item"),
    path("study_items/", views.StudyItemsTable.as_view(), name="study_items"),
    path("study_items/<uuid:pk>", views.StudyItemsRecord.as_view(), name="study_item"),
]
