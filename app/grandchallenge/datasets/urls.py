from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget
from grandchallenge.datasets.forms import labels_upload_widget
from grandchallenge.datasets.views import (
    ImageSetList,
    ImageSetDetail,
    AddImagesToImageSet,
    ImageSetUpdate,
    AnnotationSetList,
    AnnotationSetCreate,
    AddImagesToAnnotationSet,
    AnnotationSetDetail,
    AnnotationSetUpdate,
    AnnotationSetUpdateLabels,
)

app_name = "datasets"

urlpatterns = [
    path("", ImageSetList.as_view(), name="imageset-list"),
    path("<uuid:pk>/", ImageSetDetail.as_view(), name="imageset-detail"),
    path(
        "<uuid:pk>/add/",
        AddImagesToImageSet.as_view(),
        name="imageset-add-images",
    ),
    path(
        f"<uuid:pk>/add/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-imageset-image-files-ajax",
    ),
    path(
        "<uuid:pk>/update/", ImageSetUpdate.as_view(), name="imageset-update"
    ),
    path(
        "<uuid:base_pk>/annotations/",
        AnnotationSetList.as_view(),
        name="annotationset-list",
    ),
    path(
        "<uuid:base_pk>/annotations/create/",
        AnnotationSetCreate.as_view(),
        name="annotationset-create",
    ),
    path(
        "annotations/<uuid:pk>/add/",
        AddImagesToAnnotationSet.as_view(),
        name="annotationset-add-images",
    ),
    path(
        f"annotations/<uuid:pk>/add/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-annotationset-image-files-ajax",
    ),
    path(
        "annotations/<uuid:pk>/label/",
        AnnotationSetUpdateLabels.as_view(),
        name="annotationset-update-labels",
    ),
    path(
        f"annotations/<uuid:pk>/label/{labels_upload_widget.ajax_target_path}",
        labels_upload_widget.handle_ajax,
        name="labels-upload-ajax",
    ),
    path(
        "annotations/<uuid:pk>/",
        AnnotationSetDetail.as_view(),
        name="annotationset-detail",
    ),
    path(
        "annotations/<uuid:pk>/update/",
        AnnotationSetUpdate.as_view(),
        name="annotationset-update",
    ),
]
