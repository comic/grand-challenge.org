from django_filters import BooleanFilter

from grandchallenge.archives.models import Archive
from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter


class ArchiveFilter(TitleDescriptionModalityStructureFilter):
    public = BooleanFilter(label="Public", field_name="public")
    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = Archive

        search_fields = (
            *TitleDescriptionModalityStructureFilter.Meta.search_fields,
            "public",
        )
