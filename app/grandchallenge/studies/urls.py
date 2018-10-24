from django.urls import path
from grandchallenge.patients import views

app_name = "studies"
urlpatterns = [
    path('studies/&', views.StudyTable.as_view(), name="patients"),
    path('studies/(?P<pk>[0-9]+)$', views.StudyRecord.as_view(), name="patient")
]