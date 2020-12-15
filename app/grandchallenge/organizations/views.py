from django.utils.html import format_html
from django.views.generic import DetailView, ListView

from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.organizations.models import Organization


class OrganizationList(ListView):
    model = Organization
    ordering = "-created"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "jumbotron_title": "Organizations",
                "jumbotron_description": format_html(
                    (
                        "An organization is a group or institution who have "
                        "created an archive, reader study, challenge or "
                        "algorithm on this site. Please <a href='{}'>contact "
                        "us</a> if you would like to add your organization."
                    ),
                    random_encode("mailto:support@grand-challenge.org"),
                ),
            }
        )

        return context


class OrganizationDetail(DetailView):
    model = Organization
