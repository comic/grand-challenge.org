from django.views.generic import ListView

from grandchallenge.documentation.models import DocPage


class DocumentationView(ListView):
    model = DocPage
