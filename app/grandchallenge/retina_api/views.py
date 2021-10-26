from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as drf_filters
from rest_framework import mixins, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework_guardian import filters

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    ETDRSGridAnnotation,
    ImagePathologyAnnotation,
    ImageQualityAnnotation,
    ImageTextAnnotation,
    LandmarkAnnotationSet,
    OctRetinaImagePathologyAnnotation,
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
    SinglePolygonAnnotation,
)
from grandchallenge.annotations.serializers import (
    BooleanClassificationAnnotationSerializer,
    ETDRSGridAnnotationSerializer,
    ImagePathologyAnnotationSerializer,
    ImageQualityAnnotationSerializer,
    ImageTextAnnotationSerializer,
    LandmarkAnnotationSetSerializer,
    NestedPolygonAnnotationSetSerializer,
    OctRetinaImagePathologyAnnotationSerializer,
    RetinaImagePathologyAnnotationSerializer,
    SinglePolygonAnnotationSerializer,
)
from grandchallenge.cases.models import Image
from grandchallenge.cases.views import ImageViewSet
from grandchallenge.retina_api.filters import (
    RetinaAnnotationFilter,
    RetinaChildAnnotationFilter,
)
from grandchallenge.retina_api.mixins import RetinaAPIPermission
from grandchallenge.retina_api.serializers import (
    B64ImageSerializer,
    ImageLevelAnnotationsForImageSerializer,
    RetinaImageSerializer,
)


class ETDRSGridAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = ETDRSGridAnnotationSerializer
    filter_backends = (
        filters.ObjectPermissionsFilter,
        RetinaAnnotationFilter,
        drf_filters.DjangoFilterBackend,
    )
    pagination_class = None
    filterset_fields = ("image",)
    queryset = ETDRSGridAnnotation.objects.all()


class B64ThumbnailAPIView(RetrieveAPIView):
    permission_classes = (DjangoObjectPermissions, RetinaAPIPermission)
    filters = (filters.ObjectPermissionsFilter,)
    queryset = Image.objects.all()
    serializer_class = B64ImageSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        width = kwargs.get("width", settings.RETINA_DEFAULT_THUMBNAIL_SIZE)
        height = kwargs.get("height", settings.RETINA_DEFAULT_THUMBNAIL_SIZE)
        serializer_context = {"width": width, "height": height}
        serializer = B64ImageSerializer(instance, context=serializer_context)
        return Response(serializer.data)


class LandmarkAnnotationSetViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = LandmarkAnnotationSetSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None

    def get_queryset(self):
        """
        If the query parameter `image_id` is defined, the queryset will be a list of
        `LandmarkAnnotationSet`s that contain a `SingleLandmarkAnnotation` related to
        the given image id. If the image does not exist, this will raise a Http404
        Exception. Otherwise, it will return the full `LandmarkAnnotationSet` queryset

        Returns
        -------
        QuerySet
        """
        queryset = LandmarkAnnotationSet.objects.prefetch_related(
            "singlelandmarkannotation_set"
        ).all()
        image_id = self.request.query_params.get("image_id")
        if image_id is not None:
            try:
                image = get_object_or_404(Image.objects.all(), pk=image_id)
            except ValidationError:
                # Invalid uuid passed, return 404
                raise NotFound()
            queryset = LandmarkAnnotationSet.objects.filter(
                singlelandmarkannotation__image=image
            )

        return queryset


class ImageLevelAnnotationsForImageViewSet(
    mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = ImageLevelAnnotationsForImageSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)

    def get_object(self):
        keys_to_models_map = {
            "quality": ImageQualityAnnotation,
            "pathology": ImagePathologyAnnotation,
            "retina_pathology": RetinaImagePathologyAnnotation,
            "oct_retina_pathology": OctRetinaImagePathologyAnnotation,
            "text": ImageTextAnnotation,
        }
        image_id = self.kwargs.get("pk")
        if image_id is None:
            raise NotFound()
        data = {}
        for key, model in keys_to_models_map.items():
            objects = model.objects.filter(
                image__id=image_id, grader=self.request.user
            )
            try:
                data[key] = objects[0].id
            except (IndexError, AttributeError):
                data[key] = None
        return data


class QualityAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = ImageQualityAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None
    queryset = ImageQualityAnnotation.objects.all()


class PathologyAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = ImagePathologyAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None
    queryset = ImagePathologyAnnotation.objects.all()


class RetinaPathologyAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = RetinaImagePathologyAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None
    queryset = RetinaImagePathologyAnnotation.objects.all()


class OctRetinaPathologyAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = OctRetinaImagePathologyAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None
    queryset = OctRetinaImagePathologyAnnotation.objects.all()


class TextAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = ImageTextAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None
    queryset = ImageTextAnnotation.objects.all()


class PolygonAnnotationSetViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = NestedPolygonAnnotationSetSerializer
    filter_backends = (
        filters.ObjectPermissionsFilter,
        RetinaAnnotationFilter,
        drf_filters.DjangoFilterBackend,
    )
    pagination_class = None
    filterset_fields = ("image",)
    queryset = PolygonAnnotationSet.objects.all()


class SinglePolygonViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = SinglePolygonAnnotationSerializer
    filter_backends = (
        filters.ObjectPermissionsFilter,
        RetinaChildAnnotationFilter,
    )
    pagination_class = None
    queryset = SinglePolygonAnnotation.objects.all()


class BooleanClassificationAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    serializer_class = BooleanClassificationAnnotationSerializer
    filter_backends = (
        filters.ObjectPermissionsFilter,
        RetinaAnnotationFilter,
        drf_filters.DjangoFilterBackend,
    )
    pagination_class = None
    filterset_fields = ("image",)
    queryset = BooleanClassificationAnnotation.objects.all()


class RetinaImageViewSet(ImageViewSet):
    serializer_class = RetinaImageSerializer
    queryset = (
        Image.objects.all()
        .prefetch_related(
            "files",
            "singlelandmarkannotation_set__annotation_set__singlelandmarkannotation_set__image",
        )
        .select_related("modality")
    )
