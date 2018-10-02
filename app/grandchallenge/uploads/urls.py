from django.urls import path

from grandchallenge.uploads.views import (
    UploadList,
    upload_handler,
    CKUploadView,
    CKBrowseView,
)

app_name = "uploads"

urlpatterns = [
    path("", UploadList.as_view(), name="list"),
    path("create/", upload_handler, name="create"),
    path("ck/create/", CKUploadView.as_view(), name="ck-create"),
    path("ck/browse/", CKBrowseView.as_view(), name="ck-browse"),
]
