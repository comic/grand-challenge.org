from django.urls import path, include
from rest_framework.routers import DefaultRouter

from grandchallenge.workstations.views import WorkstationsViewSet

app_name = "workstations"

router = DefaultRouter()
router.register("", WorkstationsViewSet)

urlpatterns = [path("", include(router.urls))]
