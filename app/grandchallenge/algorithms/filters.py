from django_filters import BooleanFilter, FilterSet, filters

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.cases.models import Image
from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter


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
