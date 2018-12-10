from rest_framework import serializers
from .models import RetinaImage
from grandchallenge.studies.models import Study
from grandchallenge.cases.serializers import ImageSerializer


class RetinaImageSerializer(serializers.ModelSerializer):
    # allow parent relation to be empty for validation purposes
    study = serializers.PrimaryKeyRelatedField(
        queryset=Study.objects.all(), required=False
    )
    # allow image to be empty because the model is not saved yet when serializing for validation
    image = ImageSerializer(read_only=True)

    class Meta:
        model = RetinaImage
        fields = (
            "id",
            "name",
            "study",
            "image",
            "modality",
            "eye_choice",
            "voxel_size",
        )

    def get_unique_together_validators(self):
        """
        Overriding method to disable unique together checks
        """
        return []
