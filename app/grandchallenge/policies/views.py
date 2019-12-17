from django.views.generic import DetailView

from grandchallenge.policies.models import Policy


class PolicyDetail(DetailView):
    model = Policy
