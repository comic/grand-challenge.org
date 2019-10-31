from io import BytesIO

import SimpleITK
from PIL import Image as PILImage
from django.http import Http404
from rest_framework import serializers

from grandchallenge.archives.models import Archive
from grandchallenge.challenges.serializers import ImagingModalitySerializer
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.models import Study


class PILImageSerializer(serializers.BaseSerializer):
    """
    Read-only serializer that returns a PIL image from a Image instance.
    If "width" and "height" are passed as extra serializer content, the
    PIL image will be resized to those dimensions.
    If the image is 3D it will return the center slice of the image.
    """

    def to_representation(self, instance):
        try:
            image_itk = instance.get_sitk_image()
        except Exception:
            raise Http404
        pil_image = self.convert_itk_to_pil(image_itk)
        try:
            pil_image.thumbnail(
                (self.context["width"], self.context["height"]),
                PILImage.ANTIALIAS,
            )
        except KeyError:
            pass
        return pil_image

    @staticmethod
    def convert_itk_to_pil(image_itk):
        depth = image_itk.GetDepth()
        image_nparray = SimpleITK.GetArrayFromImage(image_itk)
        if depth > 0:
            # Get center slice of image if 3D
            image_nparray = image_nparray[depth // 2]
        return PILImage.fromarray(image_nparray)


class BytesImageSerializer(PILImageSerializer):
    """
    Read-only serializer that returns a BytesIO image from an Image instance.
    Subclasses PILImageSerializer, so the image may be resized and only the central
    slice of a 3d image will be returned
    """

    def to_representation(self, instance):
        image_pil = super().to_representation(instance)
        return self.create_thumbnail_as_bytes_io(image_pil)

    @staticmethod
    def create_thumbnail_as_bytes_io(image_pil):
        buffer = BytesIO()
        image_pil.save(buffer, format="png")
        return buffer.getvalue()


class TreeObjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class TreeStudySerializer(serializers.ModelSerializer):
    patient = PatientSerializer()

    class Meta:
        model = Study
        fields = ("name", "patient")


class TreeArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Archive
        fields = ("name",)


class TreeImageSerializer(TreeObjectSerializer):
    eye_choice = serializers.CharField()
    modality = ImagingModalitySerializer()
    study = TreeStudySerializer(required=False)
    archive_set = TreeArchiveSerializer(many=True)
