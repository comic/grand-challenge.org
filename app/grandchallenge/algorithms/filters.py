from django_filters import FilterSet, filters

from grandchallenge.algorithms.models import Job
from grandchallenge.cases.models import Image


class JobViewsetFilter(FilterSet):
    input_image = filters.ModelMultipleChoiceFilter(
        field_name="inputs__image", queryset=Image.objects.all(),
    )
    output_image = filters.ModelMultipleChoiceFilter(
        field_name="outputs__image", queryset=Image.objects.all(),
    )

    class Meta:
        model = Job
        fields = ["algorithm_image__algorithm", "input_image", "output_image"]
