from django.urls import path

from config.urls.rendering_subdomain import (
    urlpatterns as subdomain_urlpatterns,
)
from tests.workstations_tests.test_session_control import WorkstationView

urlpatterns = [
    *subdomain_urlpatterns,
    *[path(route=v.url_route, view=v.as_view()) for v in (WorkstationView,)],
]
