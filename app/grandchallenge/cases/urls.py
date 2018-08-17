# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget
from grandchallenge.cases.views import (
    UploadRawFiles, ShowUploadSessionState, ViewImage, AnnotationList
)

app_name = 'cases'

urlpatterns = [
    path('upload/', UploadRawFiles.as_view(), name='create'),
    path(
        f"upload/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-image-files-ajax",
    ),
    path(
        'uploaded/<uuid:pk>/',
        ShowUploadSessionState.as_view(),
        name='raw-files-session-detail',
    ),
    path(
        'image/view/<uuid:pk>/',
        ViewImage.as_view(),
        name='display-processed-image',
    ),
    path(
        'image/view/<uuid:pk>/annotations/',
        AnnotationList.as_view(),
        name='annotations-list',
    ),
]
