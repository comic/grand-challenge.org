from django.urls import path
from django.views.generic import TemplateView

from grandchallenge.well_known.views import SecurityTXT

app_name = "well_known"

urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="well_known/robots.txt", content_type="text/plain"
        ),
        name="robots_txt",
    ),
    path(".well-known/security.txt", SecurityTXT.as_view()),
]
