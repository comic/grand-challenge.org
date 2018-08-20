# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget
from grandchallenge.cases.views import (
    UploadRawFiles,
    ShowUploadSessionState,
    ViewImage,
    AnnotationList,
    AnnotationCreate,
    AnnotationDetail,
)

app_name = 'cases'

urlpatterns = [
    path('uploads/', UploadRawFiles.as_view(), name='create'),
    path(
        f"uploads/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-image-files-ajax",
    ),
    path(
        'uploads/<uuid:pk>/',
        ShowUploadSessionState.as_view(),
        name='raw-files-session-detail',
    ),
    path(
        'images/<uuid:pk>/',
        ViewImage.as_view(),
        name='display-processed-image',
    ),
    path(
        'images/<uuid:image_pk>/annotations/',
        AnnotationList.as_view(),
        name='annotation-list',
    ),
    path(
        "images/<uuid:image_pk>/annotations/create/",
        AnnotationCreate.as_view(),
        name="annotation-create",
    ),
    path(
        "images/<uuid:image_pk>/annotations/<uuid:annotation_pk>/",
        AnnotationDetail.as_view(),
        name="annotation-detail",
    ),
]
