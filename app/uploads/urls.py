from django.conf.urls import url

from uploads.views import UploadList, upload_handler

urlpatterns = [
    url(r'^$', UploadList.as_view(), name='list'),
    url(r'^create/$', upload_handler, name='create'),
]
