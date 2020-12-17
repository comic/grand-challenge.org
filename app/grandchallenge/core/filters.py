from functools import reduce
from operator import or_

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.db.models import Q
from django.forms import Form
from django_filters import CharFilter, FilterSet, ModelMultipleChoiceFilter
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

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_class(data=self.request.GET, queryset=qs).qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter": self.filter_class(self.request.GET),
                "filters_applied": any(
                    k
                    for k, v in self.request.GET.items()
                    if v and k.lower() not in ["page", "submit"]
                ),
            }
        )
        return context
