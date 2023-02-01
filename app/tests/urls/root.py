from django.urls import path

from config.urls.root import urlpatterns as root_urlpatterns
from tests.workstations_tests.test_session_control import (
    SessionControlView,
    SessionCreationView,
)

urlpatterns = [
    path("session-control/", SessionControlView.as_view()),
    path("new-session/", SessionCreationView.as_view()),
] + root_urlpatterns
