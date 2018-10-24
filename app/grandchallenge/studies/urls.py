from django.conf.urls import url
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    url(r'^studies/$', views.StudyTable.as_view()),
    url(r'^studies/(?P<pk>[0-9]+)$', views.StudyRecord.as_view())
]
