from django.conf.urls import url

from ckeditor.views import (
    upload_to_project,
    browse_project,
    upload,
    browse,
)

urlpatterns = [
    url(r'^upload/(?P<site_short_name>[\w-]+)/$', upload_to_project,
        name='ckeditor_upload_to_project'),
    url(r'^browse/(?P<site_short_name>[\w-]+)/$', browse_project,
        name='ckeditor_browse_project'),
    url(r'^upload/', upload, name='ckeditor_upload'),
    url(r'^browse/', browse, name='ckeditor_browse'),
]
