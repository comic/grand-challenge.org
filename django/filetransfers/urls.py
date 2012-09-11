from django.conf.urls.defaults import *

urlpatterns = patterns('filetransfers.views',
    (r'^$', 'upload_handler'),
    (r'^download/(?P<pk>\d+)$', 'download_handler'),
    #url(r'^(?P<site_short_name>\w+)/(?P<page_title>\w+)/$','comicsite.views.page'),
    (r'^download/(?P<project_name>\w+)/(?P<dataset_title>\w+)/(?P<filename>.+)/$', 'download_handler_filename'),
    (r'^delete/(?P<pk>.+)$', 'delete_handler'),
)
