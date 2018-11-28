from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import (
    ETDRSGridAnnotation,
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
)
from .serializers import (
    ETDRSGridAnnotationSerializer,
    MeasurementAnnotationSerializer,
    BooleanClassificationAnnotationSerializer,
    PolygonAnnotationSetSerializer,
    LandmarkAnnotationSetSerializer,
)


class ETDRSGridAnnotationViewSet(viewsets.ModelViewSet):
    queryset = ETDRSGridAnnotation.objects.all()
    serializer_class = ETDRSGridAnnotationSerializer
    permission_classes = (permissions.IsAuthenticated,)


class MeasurementAnnotationViewSet(viewsets.ModelViewSet):
    queryset = MeasurementAnnotation.objects.all()
    serializer_class = MeasurementAnnotationSerializer
    permission_classes = (permissions.IsAuthenticated,)


class BooleanClassificationAnnotationViewSet(viewsets.ModelViewSet):
    queryset = BooleanClassificationAnnotation.objects.all()
    serializer_class = BooleanClassificationAnnotationSerializer
    permission_classes = (permissions.IsAuthenticated,)


class PolygonAnnotationSetViewSet(viewsets.ModelViewSet):
    queryset = PolygonAnnotationSet.objects.all()
    serializer_class = PolygonAnnotationSetSerializer
    permission_classes = (permissions.IsAuthenticated,)


class LandmarkAnnotationSetViewSet(viewsets.ModelViewSet):
    queryset = LandmarkAnnotationSet.objects.all()
    serializer_class = LandmarkAnnotationSetSerializer
    permission_classes = (permissions.IsAuthenticated,)
