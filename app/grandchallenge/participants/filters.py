from django_filters.rest_framework import FilterSet

from grandchallenge.participants.models import RegistrationRequest


class RegistrationRequestFilter(FilterSet):
    class Meta:
        model = RegistrationRequest
        fields = ("challenge__short_name",)
