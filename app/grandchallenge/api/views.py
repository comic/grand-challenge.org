from django.conf import settings
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from grandchallenge.api.serializers import GCAPIVersionSerializer


class GCAPIView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = GCAPIVersionSerializer

    def get(self, request):
        data = {
            "latest_version": settings.GCAPI_LATEST_VERSION,
            "lowest_supported_version": settings.GCAPI_LOWEST_SUPPORTED_VERSION,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)
