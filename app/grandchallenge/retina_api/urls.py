from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.retina_api import views
from django.views.decorators.cache import cache_page
from django.conf import settings

app_name = "retina_api"

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("archives/", views.ArchiveView.as_view(), name="archives-api-view"),
    path(
        "image/<str:image_type>/<str:patient_identifier>/<str:study_identifier>/<str:image_identifier>/<str:image_modality>/",
        cache_page(settings.RETINA_IMAGE_CACHE_TIME)(views.ImageView.as_view()),
        name="image-api-view",
    ),
    path(
        "data/<str:data_type>/<int:user_id>/<str:archive_identifier>/<str:patient_identifier>/",
        views.DataView.as_view(),
        name="data-api-view",
    ),
]
