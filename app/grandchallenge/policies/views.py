from django.views.generic import TemplateView

from grandchallenge.policies.models import TermsOfService


class TermsOfServiceView(TemplateView):
    template_name = "terms_of_service.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"terms": TermsOfService.objects.first()})
        return context
