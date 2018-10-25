from django.urls import path, re_path
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    path('studies/', views.StudyTable.as_view(), name="studies"),
    re_path(r'^studies/(?P<pk>[0-9]+)$', views.StudyRecord.as_view(), name="study")
]