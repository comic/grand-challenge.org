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


class SinglePolygonAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SinglePolygonAnnotation
        fields = ("id", "value")


class PolygonAnnotationSetSerializer(serializers.ModelSerializer):
    singlepolygonannotation_set = SinglePolygonAnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = PolygonAnnotationSet
        fields = ("id", "image", "grader", "created", "name", "singlepolygonannotation_set")


class LandmarkAnnotationSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandmarkAnnotationSet
        fields = ("grader", "created")


class SingleLandmarkAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SingleLandmarkAnnotation
        fields = ("image", "annotation_set", "landmarks")
