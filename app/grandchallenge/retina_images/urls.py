from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.retina_images import views
from django.views.decorators.cache import cache_page
from django.conf import settings


router = DefaultRouter()
router.register(r"images", views.RetinaImageViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("image/thumbnail/<uuid:image_id>/", cache_page(settings.IMAGE_CACHE_TIME)(views.ThumbnailView.as_view()), name="image-thumbnail"),
    path("image/numpy/<uuid:image_id>/", cache_page(settings.IMAGE_CACHE_TIME)(views.NumpyView.as_view()),  name="image-numpy"),
]
