import base64
from io import BytesIO

import SimpleITK
from PIL import Image as PILImage
from django.http import Http404
from rest_framework import serializers

from grandchallenge.cases.models import Image
from grandchallenge.cases.serializers import HyperlinkedImageSerializer


class B64ImageSerializer(serializers.Serializer):
    """
    Serializer that returns a b64 encoded image from an Image instance.

    If "width" and "height" are passed as extra serializer content, the
    PIL image will be resized to those dimensions.

    Subclasses PILImageSerializer, so the image may be resized and only the central
    slice of a 3d image will be returned
    """

    content = serializers.SerializerMethodField(read_only=True)

    def get_content(self, obj):
        try:
            image_itk = obj.get_sitk_image()
        except Exception:
            raise Http404

        pil_image = self.convert_itk_to_pil(image_itk)

        if "width" in self.context and "height" in self.context:
            new_dims = (self.context["width"], self.context["height"])
            try:
                pil_image.thumbnail(
                    new_dims, PILImage.ANTIALIAS,
                )
            except ValueError:
                pil_image = pil_image.resize(new_dims)

        return self.create_thumbnail_as_b64(pil_image)

    @staticmethod
    def convert_itk_to_pil(image_itk):
        depth = image_itk.GetDepth()
        image_nparray = SimpleITK.GetArrayFromImage(image_itk)
        if depth > 0:
            # Get center slice of image if 3D
            image_nparray = image_nparray[depth // 2]
        return PILImage.fromarray(image_nparray)

    @staticmethod
    def create_thumbnail_as_b64(image_pil):
        buffer = BytesIO()
        image_pil.save(buffer, format="png")
        return base64.b64encode(buffer.getvalue())


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

    def get_landmark_annotations(self, obj):
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
