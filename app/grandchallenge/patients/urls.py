from django.conf.urls import url
from grandchallenge.patients import views

app_name = "api"
urlpatterns = [
    url(r'^patients/$', views.PatientTable.as_view()),
    url(r'^patients/(?P<pk>[0-9]+)$', views.PatientRecord.as_view())
]
