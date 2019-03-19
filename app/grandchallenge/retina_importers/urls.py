from django.urls import path
from grandchallenge.retina_importers import views

app_name = "importers"

urlpatterns = [
    path("check_image/", views.CheckImage.as_view(), name="check-image"),
    path("upload_image/", views.UploadImage.as_view(), name="upload-image"),
    path(
        "upload_image_registration_landmarks/",
        views.UploadLandmarkAnnotationSet.as_view(),
        name="upload-image-registration-landmarks",
    ),
    path(
        "upload_etdrs_grid_annotation/",
        views.UploadETDRSGridAnnotation.as_view(),
        name="upload-etdrs-grid-annotation",
    ),
    path(
        "upload_measurement_annotation/",
        views.UploadMeasurementAnnotation.as_view(),
        name="upload-measurement_annotation",
    ),
    path(
        "upload_boolean_classification_annotation/",
        views.UploadBooleanClassificationAnnotation.as_view(),
        name="upload-boolean-classification-annotation",
    ),
    path(
        "upload_polygon_annotation/",
        views.UploadPolygonAnnotationSet.as_view(),
        name="upload-polygon-annotation",
    ),
]
