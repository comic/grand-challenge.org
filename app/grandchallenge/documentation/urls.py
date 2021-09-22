from django.urls import path

from grandchallenge.documentation.views import DocumentationView

app_name = "documentation"

urlpatterns = [
    path("", DocumentationView.as_view(), name="list"),
]
