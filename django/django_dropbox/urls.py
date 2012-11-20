from django.conf.urls import patterns, url


urlpatterns = patterns('',

    url(r'^test/$','django_dropbox.views.test'),
    url(r'^get_connection_status/(?P<dropbox_folder_id>\w+)/$','django_dropbox.views.get_connection_status'),    
    url(r'^reset_connection/(?P<dropbox_folder_id>\w+)/$','django_dropbox.views.reset_connection'),
    url(r'^finalize_connection/(?P<dropbox_folder_id>\w+)/$','django_dropbox.views.finalize_connection'),
    
    
)
    