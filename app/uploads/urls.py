from django.conf.urls import url

from uploads.views import UploadList

urlpatterns = [
    url(r'^$', UploadList.as_view(), name='list'),
]
