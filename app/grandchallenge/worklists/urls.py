from django.conf.urls import url
from pathology_worklist.api import views

app_name = "api"
urlpatterns = [
    url(r'^worklists/$', views.WorklistTable.as_view()),
    url(r'^worklists/(?P<pk>[0-9]+)$', views.WorklistRecord.as_view()),
    url(r'^worklist_patient_relations/$', views.WorklistPatientRelationTable.as_view()),
    url(r'^worklist_patient_relations/(?P<pk>[0-9]+)$', views.WorklistPatientRelationRecord.as_view())
]
