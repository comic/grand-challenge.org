from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.archives import views

router = DefaultRouter()
router.register(r"archives", views.ArchiveViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
