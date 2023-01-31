from django.urls import path

from config.urls.root import urlpatterns as root_urlpatterns
from tests.workstations_tests.test_session_control import (
    SessionControlView,
    SessionCreationView,
)

urlpatterns = [
    *root_urlpatterns,
    *[
        path(route=v.url_route, view=v.as_view())
        for v in (
            SessionControlView,
            SessionCreationView,
        )
    ],
]
