from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer

from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudySerializer(HyperlinkedModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")

    class Meta:
        model = ReaderStudy
        fields = (
            "pk",
            "title",
            "creator",
            "description",
            "hanging_list_images",
            "is_valid",
        )
