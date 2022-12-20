from uuid import UUID

from rest_framework import serializers

from grandchallenge.cases.models import Image
from grandchallenge.cases.serializers import HyperlinkedImageSerializer


class ImageLevelAnnotationsForImageSerializer(serializers.Serializer):
    quality = serializers.UUIDField(allow_null=True, read_only=True)
    pathology = serializers.UUIDField(allow_null=True, read_only=True)
    retina_pathology = serializers.UUIDField(allow_null=True, read_only=True)
    oct_retina_pathology = serializers.UUIDField(
        allow_null=True, read_only=True
    )
    text = serializers.UUIDField(allow_null=True, read_only=True)


class RetinaImageSerializer(HyperlinkedImageSerializer):
    landmark_annotations = serializers.SerializerMethodField(read_only=True)

    def get_landmark_annotations(self, obj) -> list[UUID]:
        return [
            sla2.image.pk
            for sla1 in obj.singlelandmarkannotation_set.all()
            for sla2 in sla1.annotation_set.singlelandmarkannotation_set.all()
            if sla1.image.pk != sla2.image.pk
        ]

    class Meta:
        model = Image
        fields = (
            *HyperlinkedImageSerializer.Meta.fields,
            "landmark_annotations",
        )
