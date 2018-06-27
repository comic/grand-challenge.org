# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget, \
    duplicate_file_rejecter
from grandchallenge.cases.views import UploadRawFiles, \
    ShowUploadSessionState, ViewImage

app_name = 'cases'

urlpatterns = [
    path('upload/', UploadRawFiles.as_view(), name='create'),
    path(
        f"upload/{upload_raw_files_widget.ajax_target_path}",
        duplicate_file_rejecter.install_request_updater(
            upload_raw_files_widget.handle_ajax),
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
]
