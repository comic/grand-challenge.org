from django.conf.urls import url
from django.urls import path

from grandchallenge.pages.views import (
    page, insertedpage, PageList, PageCreate, PageUpdate, PageDelete,
    FaviconView)

app_name = 'pages'

urlpatterns = [
    url(r'^pages/$', PageList.as_view(), name='list'),
    url(r'^pages/create/$', PageCreate.as_view(), name='create'),

    # Favicons
    path(
        'favicon.ico/',
        FaviconView.as_view(rel='shortcut icon'),
        name='favicon',
    ),
    path(
        'apple-touch-icon.png/',
        FaviconView.as_view(rel='apple-touch-icon'),
        name='apple-touch-icon',
    ),
    path(
        'apple-touch-icon-precomposed.png/',
        FaviconView.as_view(rel='apple-touch-icon-precomposed'),
        name='apple-touch-icon-precomposed',
    ),
    path(
        'apple-touch-icon-<int:size>x<int>.png/',
        FaviconView.as_view(rel='apple-touch-icon'),
        name='apple-touch-icon-sized',
    ),
    path(
        'apple-touch-icon-<int:size>x<int>-precomposed.png/',
        FaviconView.as_view(rel='apple-touch-icon-precomposed'),
        name='apple-touch-icon-precomposed-sized',
    ),

    url(r'^(?P<page_title>[\w-]+)/$', page, name='detail'),
    url(
        r'^(?P<page_title>[\w-]+)/update/$',
        PageUpdate.as_view(),
        name='update',
    ),
    url(
        r'^(?P<page_title>[\w-]+)/delete/$',
        PageDelete.as_view(),
        name='delete',
    ),
    url(
        r'^(?P<page_title>[\w-]+)/insert/(?P<dropboxpath>.+)/$',
        insertedpage,
        name='insert-detail',
    ),
]
