from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.studies import views

router = DefaultRouter()
router.register(r"studies", views.StudyViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
