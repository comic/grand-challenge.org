from django.conf.urls import url

from filetransfers.views import (
    upload_handler,
    download_handler,
    uploadedfileserve_handler,
    delete_handler,
)

urlpatterns = [
    url(r'^$', upload_handler, name='upload'),
    url(r'^download/(?P<pk>\d+)$', download_handler, name='download'),
    url(r'^serve/(?P<pk>\d+)$', uploadedfileserve_handler, name='serve'),
    url(r'^delete/(?P<pk>.+)$', delete_handler, name='delete'),
]
