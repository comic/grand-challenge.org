from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.uploads.models import UserUpload, UserUploadFile
from grandchallenge.uploads.serializers import (
    FileCompleteSerializer,
    PresignedURLSerializer,
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

    @action(
        detail=True,
        methods=["patch"],
        serializer_class=PresignedURLSerializer,
    )
    def generate_presigned_url(self, request, pk):
        object = self.get_object()
        serializer = self.get_serializer(
            instance=object, data=request.data, partial=True
        )

        if serializer.is_valid():
            return Response(data=serializer.data)
        else:
            return Response(
                data=serializer.errors, status=HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True, methods=["patch"], serializer_class=FileCompleteSerializer
    )
    def complete_multipart_upload(self, request, pk):
        object = self.get_object()
        serializer = self.get_serializer(
            instance=object, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data)
        else:
            return Response(
                data=serializer.errors, status=HTTP_400_BAD_REQUEST
            )
