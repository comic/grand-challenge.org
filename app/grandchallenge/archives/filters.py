from grandchallenge.archives.models import Archive
from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter


class ArchiveFilter(TitleDescriptionModalityStructureFilter):
    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = Archive
