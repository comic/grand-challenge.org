from django.conf.urls import url

from pages.views import page, insertedpage

urlpatterns = [
    url(r'^(?P<page_title>[\w-]+)/$', page, name='page-detail'),
    url(r'^(?P<page_title>[\w-]+)/insert/(?P<dropboxpath>.+)/$', insertedpage,
        name='insertpage-detail'),
]
