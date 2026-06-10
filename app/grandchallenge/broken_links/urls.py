from django.urls import path

from grandchallenge.broken_links.views import BrokenLinkDashboard

app_name = "broken-links"

urlpatterns = [
    path("", BrokenLinkDashboard.as_view(), name="dashboard"),
]
