from django.conf.urls import url

from filetransfers.views import (
    upload_handler,
    download_handler,
    uploadedfileserve_handler,
    delete_handler,
)

urlpatterns = [
    url(r'^$', upload_handler),
    url(r'^download/(?P<pk>\d+)$', download_handler),
    url(r'^serve/(?P<pk>\d+)$', uploadedfileserve_handler),
    url(r'^delete/(?P<pk>.+)$', delete_handler),
]
