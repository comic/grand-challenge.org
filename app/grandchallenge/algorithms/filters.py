from django_filters import BooleanFilter, FilterSet, filters
from rest_framework.filters import BaseFilterBackend

from grandchallenge.algorithms.models import (
    Algorithm,
    Endpoint,
    Invocation,
    Job,
)
from grandchallenge.cases.models import Image
from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter
from grandchallenge.core.guardian import filter_by_permission


class EndpointFilter(FilterSet):
    algorithm = filters.ModelChoiceFilter(
        field_name="algorithm_image__algorithm",
        queryset=Algorithm.objects.all(),
    )
    status = filters.CharFilter(method="filter_status")

    class Meta:
        model = Endpoint
        fields = ["algorithm", "status"]

    def filter_status(self, queryset, name, value):
        display_to_value = {
            label.lower(): db_value
            for db_value, label in Endpoint.StatusChoices.choices
        }

        try:
            return queryset.filter(status=display_to_value[value.lower()])
        except KeyError:
            return queryset.none()


class EndpointObjectPermissionsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        endpoints = filter_by_permission(
            queryset=Endpoint.objects.all(),
            user=request.user,
            codename="view_endpoint",
        )
        return queryset.filter(endpoint__in=endpoints)


class InvocationFilter(FilterSet):
    status = filters.CharFilter(method="filter_status")

    class Meta:
        model = Invocation
        fields = ["endpoint", "status"]

    def filter_status(self, queryset, name, value):
        display_to_value = {
            label.lower(): db_value
            for db_value, label in Invocation.StatusChoices.choices
        }

        try:
            return queryset.filter(status=display_to_value[value.lower()])
        except KeyError:
            return queryset.none()


class JobViewsetFilter(FilterSet):
    input_image = filters.ModelMultipleChoiceFilter(
        field_name="inputs__image", queryset=Image.objects.all()
    )
    output_image = filters.ModelMultipleChoiceFilter(
        field_name="outputs__image", queryset=Image.objects.all()
    )

    class Meta:
        model = Job
        fields = ["algorithm_image__algorithm", "input_image", "output_image"]


class AlgorithmFilter(TitleDescriptionModalityStructureFilter):
    public = BooleanFilter(label="Public", field_name="public")

    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = Algorithm
        search_fields = (
            *TitleDescriptionModalityStructureFilter.Meta.search_fields,
            "public",
        )
