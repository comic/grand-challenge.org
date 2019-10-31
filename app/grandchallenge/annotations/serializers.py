from rest_framework import serializers

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    ETDRSGridAnnotation,
    ImagePathologyAnnotation,
    ImageQualityAnnotation,
    ImageTextAnnotation,
    LandmarkAnnotationSet,
    MeasurementAnnotation,
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
    SingleLandmarkAnnotation,
    SinglePolygonAnnotation,
)
from grandchallenge.annotations.validators import (
    validate_grader_is_current_retina_user,
)


class AbstractAnnotationSerializer(serializers.ModelSerializer):
    def validate_grader(self, value):
        """
        Validate that grader is the user creating the object for retina_graders group
        """
        validate_grader_is_current_retina_user(value, self.context)
        return value

    class Meta:
        abstract = True


class AbstractSingleAnnotationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        """
        Validate that the user that is creating this object equals the
        annotation_set.grader for retina_graders
        """
        if data.get("annotation_set") is None:
            return data

        grader = data["annotation_set"].grader
        validate_grader_is_current_retina_user(grader, self.context)
        return data

    class Meta:
        abstract = True


class ETDRSGridAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = ETDRSGridAnnotation
        fields = ("id", "grader", "created", "image", "fovea", "optic_disk")


class MeasurementAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = MeasurementAnnotation
        fields = ("image", "grader", "created", "start_voxel", "end_voxel")


class BooleanClassificationAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = BooleanClassificationAnnotation
        fields = ("image", "grader", "created", "name", "value")


class SinglePolygonAnnotationSerializer(AbstractSingleAnnotationSerializer):
    annotation_set = serializers.PrimaryKeyRelatedField(
        queryset=PolygonAnnotationSet.objects.all()
    )

    class Meta:
        model = SinglePolygonAnnotation
        fields = (
            "id",
            "value",
            "annotation_set",
            "created",
            "x_axis_orientation",
            "y_axis_orientation",
            "z",
        )


class PolygonAnnotationSetSerializer(AbstractAnnotationSerializer):
    singlepolygonannotation_set = SinglePolygonAnnotationSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = PolygonAnnotationSet
        fields = (
            "id",
            "image",
            "grader",
            "created",
            "name",
            "singlepolygonannotation_set",
        )


class SingleLandmarkAnnotationSerializer(AbstractSingleAnnotationSerializer):
    class Meta:
        model = SingleLandmarkAnnotation
        fields = ("image", "annotation_set", "landmarks")


class LandmarkAnnotationSetSerializer(AbstractAnnotationSerializer):
    singlelandmarkannotation_set = SingleLandmarkAnnotationSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = LandmarkAnnotationSet
        fields = ("id", "grader", "created", "singlelandmarkannotation_set")


class ImageQualityAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = ImageQualityAnnotation
        fields = (
            "id",
            "created",
            "grader",
            "image",
            "quality",
            "quality_reason",
        )


class ImagePathologyAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = ImagePathologyAnnotation
        fields = ("id", "created", "grader", "image", "pathology")


class RetinaImagePathologyAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = RetinaImagePathologyAnnotation
        fields = (
            "id",
            "created",
            "grader",
            "image",
            "amd_present",
            "dr_present",
            "oda_present",
            "myopia_present",
            "cysts_present",
            "other_present",
        )


class ImageTextAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = ImageTextAnnotation
        fields = ("id", "created", "grader", "image", "text")
