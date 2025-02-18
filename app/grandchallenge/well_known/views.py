from django.contrib.sites.models import Site
from django.views.generic import TemplateView


class SecurityTXT(TemplateView):
    template_name = "well_known/security.txt"
    content_type = "text/plain"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_site"] = Site.objects.get_current(
            request=self.request
        )
        return context
