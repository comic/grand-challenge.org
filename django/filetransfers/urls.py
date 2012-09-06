from django.conf.urls.defaults import *

urlpatterns = patterns('filetransfers.views',
    (r'^$', 'upload_handler'),
    (r'^download/(?P<pk>.+)$', 'download_handler'),
    (r'^delete/(?P<pk>.+)$', 'delete_handler'),
)
