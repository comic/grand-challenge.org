from django.urls import path

from grandchallenge.uploads.views import UploadList, upload_handler

app_name = "uploads"

urlpatterns = [
    path("", UploadList.as_view(), name="list"),
    path("create/", upload_handler, name="create"),
]
