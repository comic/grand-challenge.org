from django.conf.urls import *

urlpatterns = patterns('filetransfers.views',
                       (r'^$', 'upload_handler'),
                       (r'^download/(?P<pk>\d+)$', 'download_handler'),
                       (r'^serve/(?P<pk>\d+)$', 'uploadedfileserve_handler'),
                       (r'^delete/(?P<pk>.+)$', 'delete_handler'),
                       )
