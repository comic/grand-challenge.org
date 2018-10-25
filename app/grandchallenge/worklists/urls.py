from django.urls import path, re_path
from grandchallenge.worklists import views

app_name = "api"
urlpatterns = [
    path('worklists/', views.WorklistTable.as_view(), name="worklists"),
    re_path(r'^worklists/(?P<pk>[0-9]+)$', views.WorklistRecord.as_view(), name="worklist"),
    path('worklist_patient_relations/', views.WorklistPatientRelationTable.as_view(), name="relations"),
    re_path(r'^worklist_patient_relations/(?P<pk>[0-9]+)$', views.WorklistPatientRelationRecord.as_view(), name="relation")
]
