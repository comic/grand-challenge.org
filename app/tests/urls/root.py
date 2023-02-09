from django.urls import path

from config.urls.root import urlpatterns as root_urlpatterns
from tests.workstations_tests.test_session_control import (
    SessionControlView,
    SessionCreationView,
    WorkstationView,
)
from tests.workstations_tests.test_templatetags import (
    RSWorkstationButtonTestView,
)

urlpatterns = [
    path(
        "session-control/",
        SessionControlView.as_view(),
        name="session-control-test",
    ),
    path(
        "new-session/", SessionCreationView.as_view(), name="new-session-test"
    ),
    path("workstation/", WorkstationView.as_view(), name="workstation-mock"),
    path(
        "<slug>/rs-workstation-button/",
        RSWorkstationButtonTestView.as_view(),
        name="rs-workstation-button",
    ),
] + root_urlpatterns
