from django.conf.urls import url

from uploads.views import (
    UploadList, upload_handler, CKUploadView, CKBrowseView
)

urlpatterns = [
    url(r'^$', UploadList.as_view(), name='list'),
    url(r'^create/$', upload_handler, name='create'),
    url(r'^ck/create/$', CKUploadView.as_view(), name='ck-create'),
    url(r'^ck/browse/$', CKBrowseView.as_view(), name='ck-browse'),
]
