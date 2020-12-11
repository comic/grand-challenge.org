from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter
from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudyFilter(TitleDescriptionModalityStructureFilter):
    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = ReaderStudy
