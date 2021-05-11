from django_filters import FilterSet, ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget

from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image


class ImageFilterSet(FilterSet):
    archive = ModelMultipleChoiceFilter(
        queryset=Archive.objects.all(),
        widget=Select2MultipleWidget,
        label="Archive",
        field_name="componentinterfacevalue__archive_items__archive__pk",
        to_field_name="pk",
    )

    class Meta:
        model = Image
        fields = (
            "study",
            "origin",
            # TODO JM: Add algorithm jobs here and remove from serializer
            "archive",
            "readerstudies",
            "name",
        )
