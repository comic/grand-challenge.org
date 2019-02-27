from django.urls import include, path
from rest_framework.routers import DefaultRouter

from grandchallenge.mlmodels.views import MLModelViewSet

app_name = "mlmodels"

router = DefaultRouter()
router.register(r"", MLModelViewSet)

urlpatterns = [path("", include(router.urls))]
