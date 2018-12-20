from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grandchallenge.patients import views

app_name = "patients"

router = DefaultRouter()
router.register(r"patients", views.PatientViewSet)

urlpatterns = [path("", include(router.urls))]
