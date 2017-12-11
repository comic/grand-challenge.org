from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'filetransfers.views.upload_handler'),
    url(r'^download/(?P<pk>\d+)$', 'filetransfers.views.download_handler'),
    url(r'^serve/(?P<pk>\d+)$',
        'filetransfers.views.uploadedfileserve_handler'),
    url(r'^delete/(?P<pk>.+)$', 'filetransfers.views.delete_handler'),
]
