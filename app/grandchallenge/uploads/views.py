from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.uploads.models import UserUpload, UserUploadFile
from grandchallenge.uploads.serializers import (
    UserUploadFileSerializer,
    UserUploadSerializer,
)


class UserUploadViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = UserUploadSerializer
    queryset = UserUpload.objects.all()
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ObjectPermissionsFilter,)


class UserUploadFileViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = UserUploadFileSerializer
    queryset = UserUploadFile.objects.all()
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ObjectPermissionsFilter,)

    @action(detail=True, methods=["patch"])
    def generate_presigned_url(self, request, pk):
        raise NotImplementedError

    @action(detail=True, methods=["patch"])
    def complete_multipart_upload(self, request, pk):
        raise NotImplementedError
