from django.urls import path
from grandchallenge.pathology import views

app_name = "pathology"
urlpatterns = [
    path("patient_items/", views.PatientItemTable.as_view(), name="patient-items"),
    path("patient_items/<uuid:pk>/", views.PatientItemRecord.as_view(), name="patient-item"),
    path("patient_items/create/", views.PatientItemCreateView.as_view(), name="patient-item-create"),
    path("patient_items/remove/<uuid:pk>/", views.PatientItemRemoveView.as_view(),
         name="patient-item-remove"),
    path("patient_items/update/<uuid:pk>/", views.PatientItemUpdateView.as_view(),
         name="patient-item-update"),
    path("patient_items/display/", views.PatientItemDisplayView.as_view(), name="patient-item-display"),
    path("study_items/", views.StudyItemTable.as_view(), name="study-items"),
    path("study_items/<uuid:pk>/", views.StudyItemRecord.as_view(), name="study-item"),
    path("study_items/create/", views.StudyItemCreateView.as_view(), name="study-item-create"),
    path("study_items/remove/<uuid:pk>/", views.StudyItemRemoveView.as_view(), name="study-item-remove"),
    path("study_items/update/<uuid:pk>/", views.StudyItemUpdateView.as_view(), name="study-item-update"),
    path("study_items/display/", views.StudyItemDisplayView.as_view(), name="study-item-display"),
    path("worklist_items/", views.WorklistItemTable.as_view(), name="worklist-items"),
    path("worklist_items/<uuid:pk>/", views.WorklistItemRecord.as_view(), name="worklist-item"),
    path("worklist_items/create/", views.WorklistItemCreateView.as_view(), name="worklist-item-create"),
    path("worklist_items/remove/<uuid:pk>/", views.WorklistItemRemoveView.as_view(),
         name="worklist-item-remove"),
    path("worklist_items/update/<uuid:pk>/", views.WorklistItemUpdateView.as_view(),
         name="worklist-item-update"),
    path("worklist_items/display/", views.WorklistItemDisplayView.as_view(), name="worklist-item-display"),
]
