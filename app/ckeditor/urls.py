from django.conf.urls import url

urlpatterns = [
    url(r'^upload/(?P<site_short_name>[\w-]+)/$',
        'ckeditor.views.upload_to_project',
        name='ckeditor_upload_to_project'),
    url(r'^browse/(?P<site_short_name>[\w-]+)/$',
        'ckeditor.views.browse_project', name='ckeditor_browse_project'),
    url(r'^upload/', 'ckeditor.views.upload', name='ckeditor_upload'),
    url(r'^browse/', 'ckeditor.views.browse', name='ckeditor_browse'),
]
