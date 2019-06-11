from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer

from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudySerializer(HyperlinkedModelSerializer):
    images = HyperlinkedRelatedField(
        view_name="api:image-detail", many=True, read_only=True
    )
    creator = SlugRelatedField(read_only=True, slug_field="username")

    class Meta:
        model = ReaderStudy
        fields = (
            "pk",
            "title",
            "creator",
            "description",
            "hanging_list",
            "images",
        )
