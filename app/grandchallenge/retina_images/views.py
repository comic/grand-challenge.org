from rest_framework import permissions, viewsets
from django.shortcuts import get_object_or_404
from django.views import View
from PIL import Image as PILImage
from django.http.response import HttpResponse
import numpy as np
from grandchallenge.retina_api.mixins import RetinaAPIPermissionMixin
from .models import RetinaImage
from .serializers import RetinaImageSerializer


class RetinaImageViewSet(viewsets.ModelViewSet):
    queryset = RetinaImage.objects.all()
    serializer_class = RetinaImageSerializer
    permission_classes = (permissions.IsAuthenticated,)


"""
RetinaImage custom views
"""


class ThumbnailView(View):
    """
    View class for returning a thumbnail of an image (max height/width: 128px)
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, image_id):
        image_object = get_object_or_404(RetinaImage, pk=image_id)
        image = PILImage.open(image_object.image.path)
        image.thumbnail((128, 128), PILImage.ANTIALIAS)
        response = HttpResponse(content_type="image/png")
        image.save(response, "png")
        return response


class NumpyView(View):
    """
    View class for returning a numpy array of a specific image
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, image_id):
        image_object = get_object_or_404(RetinaImage, pk=image_id)

        if image_object.modality == RetinaImage.MODALITY_OCT:
            # return all 128 images as list of numpy arrays
            npy = image_object.get_all_oct_images_as_npy()
        else:
            # normal image, return as numpy array
            image = PILImage.open(image_object.image.path)
            npy = np.array(image)

        # return numpy array as response
        response = HttpResponse(content_type="application/octet-stream")
        np.save(response, npy)
        return response
