from django.urls import path

from config.urls.root import urlpatterns as root_urlpatterns
from tests.workstations_tests.test_session_control import (
    SessionControlView,
    SessionCreationView,
    WorkstationView,
)

handler500 = "grandchallenge.core.views.handler500"

urlpatterns = [
    path(
        "session-control/",
        SessionControlView.as_view(),
        name="session-control-test",
    ),
    path(
        "new-session/", SessionCreationView.as_view(), name="new-session-test"
    ),
    path(
        "new-session/path-param/12345/",
        SessionCreationView.as_view(),
        name="new-session-test-with-path-param",
    ),
    path("workstation/", WorkstationView.as_view(), name="workstation-mock"),
    *root_urlpatterns,
]
