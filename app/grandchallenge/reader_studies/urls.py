from django.urls import path

from grandchallenge.reader_studies.views import ReaderStudyList

app_name = "reader-studies"

urlpatterns = [path("", ReaderStudyList.as_view(), name="list")]
