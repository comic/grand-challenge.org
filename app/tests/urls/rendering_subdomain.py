from django.urls import path

from config.urls.rendering_subdomain import (
    urlpatterns as subdomain_urlpatterns,
)
from tests.workstations_tests.test_session_control import WorkstationView

urlpatterns = [
    path(
        "workstation/",
        WorkstationView.as_view(),
    ),
] + subdomain_urlpatterns
