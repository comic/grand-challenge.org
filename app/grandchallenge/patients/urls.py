from django.conf.urls import url
from grandchallenge.patients import views

app_name = "patients"
urlpatterns = [
    url(r'^/$', views.PatientTable.as_view()),
    url(r'^/(?P<pk>[0-9]+)$', views.PatientRecord.as_view())
]
