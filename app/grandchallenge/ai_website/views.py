from django.views.generic import TemplateView


class HomeTemplate(TemplateView):
    template_name = "ai_website/base.html"
