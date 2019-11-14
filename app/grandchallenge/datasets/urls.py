from django.urls import path

from grandchallenge.datasets.views import (
    AddImagesToAnnotationSet,
    AddImagesToImageSet,
    AnnotationSetCreate,
    AnnotationSetDetail,
    AnnotationSetList,
    AnnotationSetUpdate,
    AnnotationSetUpdateLabels,
    ImageSetDetail,
    ImageSetList,
    ImageSetUpdate,
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
        "annotations/<uuid:pk>/label/",
        AnnotationSetUpdateLabels.as_view(),
        name="annotationset-update-labels",
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
