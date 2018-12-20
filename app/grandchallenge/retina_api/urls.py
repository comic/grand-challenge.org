from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.retina_api import views
from django.views.decorators.cache import cache_page
from django.conf import settings

app_name = "api"

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path(
        "archives/",
        # cache_page(settings.RETINA_ARCHIVES_REQUEST_CACHE_TIME)(views.ArchiveView.as_view()),
        views.ArchiveView.as_view(),
        name="archives-api-view",
    ),
    path(
        "image/<str:image_type>/<str:patient_identifier>/<str:study_identifier>/<str:image_identifier>/<str:image_modality>/",
        views.ImageView.as_view(),
        name="image-api-view",
    ),
    # path("image/original/<str:patient_identifier>/<str:study_identifier>/<str:series_identifier>/<str:image_name>/", views.OriginalImageView.as_view()),
    path(
        "data/<str:data_type>/<str:username>/<str:archive_identifier>/<str:patient_identifier>/",
        cache_page(settings.RETINA_IMAGE_CACHE_TIME)(views.DataView.as_view()),
        name="data-api-view",
    ),
]
