from django.urls import include, path
from rest_framework.routers import DefaultRouter

from grandchallenge.registrations import views

app_name = "registrations"

router = DefaultRouter()
router.register(r"oct_obs_registrations", views.OctObsRegistrationViewSet)

urlpatterns = [path("", include(router.urls))]
