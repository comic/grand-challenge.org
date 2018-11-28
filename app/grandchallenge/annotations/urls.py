from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.annotations import views


router = DefaultRouter()
router.register(r"etdrs_grid_placement", views.ETDRSGridAnnotationViewSet)
router.register(r"measurement_annotation", views.MeasurementAnnotationViewSet)
router.register(
    r"boolean_image_level_annotation", views.BooleanClassificationAnnotationViewSet
)
router.register(r"polygon_annotation", views.PolygonAnnotationSetViewSet)
router.register(r"landmark_annotation", views.LandmarkAnnotationSetViewSet)
urlpatterns = [path("", include(router.urls))]
