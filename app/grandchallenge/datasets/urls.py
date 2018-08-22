# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget
from grandchallenge.datasets.views import (
    ImageSetList,
    ImageSetCreate,
    ImageSetDetail,
    AddImagesToImageSet,
    ImageSetUpdate,
    AnnotationSetList,
)

app_name = "datasets"

urlpatterns = [
    path("", ImageSetList.as_view(), name="imageset-list"),
    path("create/", ImageSetCreate.as_view(), name="imageset-create"),
    path("<uuid:pk>/", ImageSetDetail.as_view(), name="imageset-detail"),
    path(
        "<uuid:pk>/add/",
        AddImagesToImageSet.as_view(),
        name="imageset-add-images",
    ),
    path(
        f"<uuid:pk>/add/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-image-files-ajax",
    ),
    path(
        "<uuid:pk>/update/", ImageSetUpdate.as_view(), name="imageset-update"
    ),
    path(
        "<uuid:base_pk>/annotations/",
        AnnotationSetList.as_view(),
        name="annotationset-list",
    ),
]
