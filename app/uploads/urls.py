from django.conf.urls import url

from uploads.views import (
    UploadList,
    upload_handler,
    CKUploadView,
    ck_browse_uploads,
)

urlpatterns = [
    url(r'^$', UploadList.as_view(), name='list'),
    url(r'^create/$', upload_handler, name='create'),
    url(r'^ck/create/$', CKUploadView.as_view(), name='ck-create'),
    url(r'^ck/browse/$', ck_browse_uploads, name='ck-browse'),
]
