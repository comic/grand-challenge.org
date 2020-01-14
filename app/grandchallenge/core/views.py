from django.views.generic import TemplateView


class HomeTemplate(TemplateView):
    template_name = "home.html"
