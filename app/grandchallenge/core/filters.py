from functools import reduce
from operator import or_

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.core.validators import EMPTY_VALUES
from django.db.models import Q
from django.forms import Form
from django_filters import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    ModelMultipleChoiceFilter,
)
from django_select2.forms import Select2MultipleWidget

from grandchallenge.anatomy.models import BodyRegion, BodyStructure
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization


class FilterForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = "GET"
        self.helper.layout.append(Submit("submit", "Apply Filters"))


class TitleDescriptionModalityStructureFilter(FilterSet):
    search = CharFilter(method="search_filter", label="Title or Description")
    modalities = ModelMultipleChoiceFilter(
        queryset=ImagingModality.objects.all(),
        widget=Select2MultipleWidget,
        label="Modality",
    )
    structures = ModelMultipleChoiceFilter(
        queryset=BodyStructure.objects.select_related("region").all(),
        widget=Select2MultipleWidget,
        label="Anatomical Structure",
    )
    structures__region = ModelMultipleChoiceFilter(
        queryset=BodyRegion.objects.all(),
        widget=Select2MultipleWidget,
        label="Anatomical Region",
    )
    organizations = ModelMultipleChoiceFilter(
        queryset=Organization.objects.all(),
        widget=Select2MultipleWidget,
        label="Organization",
        field_name="organizations__slug",
        to_field_name="slug",
    )

    class Meta:
        fields = (
            "search",
            "modalities",
            "structures",
            "structures__region",
            "organizations",
        )
        form = FilterForm
        search_fields = ("title", "description")

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            reduce(
                or_,
                [
                    Q(**{f"{f}__icontains": value})
                    for f in self.Meta.search_fields
                ],
                Q(),
            )
        )


class FilterMixin:
    filter_class = None
    total_count = 0
    num_results = 0

    def get_queryset(self):
        qs = super().get_queryset()
        self.total_count = qs.count()
        filtered_qs = self.filter_class(data=self.request.GET, queryset=qs).qs
        self.num_results = filtered_qs.count()
        return filtered_qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "num_results": self.num_results,
                "total_count": self.total_count,
                "filter": self.filter_class(self.request.GET),
                "filters_applied": any(
                    k
                    for k, v in self.request.GET.items()
                    if v and k.lower() not in ["page", "submit"]
                ),
            }
        )
        return context


class EmptyStringFilter(BooleanFilter):
    # https://django-filter.readthedocs.io/en/latest/guide/tips.html#solution-2-empty-string-filter
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        exclude = self.exclude ^ (value is False)
        method = qs.exclude if exclude else qs.filter

        return method(**{self.field_name: ""})
