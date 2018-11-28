from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.registrations import views

router = DefaultRouter()
router.register(r"oct_obs_registrations", views.OctObsRegistrationViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
