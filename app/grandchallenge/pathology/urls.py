from django.urls import path, re_path
from grandchallenge.pathology import views

app_name = "pathology"
urlpatterns = [
    path('worklist_items/', views.WorklistItemsTable.as_view(), name="worklist_items"),
    re_path(r'^worklist_items/(?P<pk>[0-9]+)$', views.WorklistItemsRecord.as_view(), name="worklist_item"),
    path('patient_items/', views.PatientItemsTable.as_view(), name="patient_items"),
    re_path(r'^patient_items/(?P<pk>[0-9]+)$', views.PatientItemsRecord.as_view(), name="patient_item"),
    path('study_items/', views.StudyItemsTable.as_view(), name="study_items"),
    re_path(r'^study_items/(?P<pk>[0-9]+)$', views.StudyItemsRecord.as_view(), name="study_item"),
]
