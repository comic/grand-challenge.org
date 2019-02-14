from rest_framework import serializers
from .models import (
    ETDRSGridAnnotation,
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
    SingleLandmarkAnnotation,
)


class ETDRSGridAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ETDRSGridAnnotation
        fields = ("grader", "created", "image", "fovea", "optic_disk")


class MeasurementAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasurementAnnotation
        fields = ("image", "grader", "created", "start_voxel", "end_voxel")


class BooleanClassificationAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BooleanClassificationAnnotation
        fields = ("image", "grader", "created", "name", "value")


class PolygonAnnotationSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolygonAnnotationSet
        fields = ("image", "grader", "created", "name")


class LandmarkAnnotationSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandmarkAnnotationSet
        fields = ("grader", "created")


class SingleLandmarkAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SingleLandmarkAnnotation
        fields = ("image", "annotation_set", "landmarks")
