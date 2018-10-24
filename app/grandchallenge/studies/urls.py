from django.conf.urls import url
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    url(r'^/$', views.StudyTable.as_view()),
    url(r'^/(?P<pk>[0-9]+)$', views.StudyRecord.as_view())
]
