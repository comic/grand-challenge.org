from rest_framework import serializers

from .models import (
    ETDRSGridAnnotation,
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    PolygonAnnotationSet,
    SinglePolygonAnnotation,
    LandmarkAnnotationSet,
    SingleLandmarkAnnotation,
)
from .validators import validate_grader_is_current_retina_user


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
        Validate that the user that is creating this object equals the annotation_set.grader for retina_graders
        """
        validate_grader_is_current_retina_user(
            data["annotation_set"].grader, self.context
        )
        return data

    class Meta:
        abstract = True


class ETDRSGridAnnotationSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = ETDRSGridAnnotation
        fields = ("grader", "created", "image", "fovea", "optic_disk")


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
        fields = ("id", "value", "annotation_set")


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


class LandmarkAnnotationSetSerializer(AbstractAnnotationSerializer):
    class Meta:
        model = LandmarkAnnotationSet
        fields = ("grader", "created")


class SingleLandmarkAnnotationSerializer(AbstractSingleAnnotationSerializer):
    class Meta:
        model = SingleLandmarkAnnotation
        fields = ("image", "annotation_set", "landmarks")
