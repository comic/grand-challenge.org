from django.urls import path, re_path
from grandchallenge.patients import views

app_name = "studies"
urlpatterns = [
    path('studies/', views.StudyTable.as_view(), name="patients"),
    re_path('studies/(?P<pk>[0-9]+)$', views.StudyRecord.as_view(), name="patient")
]