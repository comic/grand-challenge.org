from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.serializers import (
    UserUploadCompleteSerializer,
    UserUploadCreateSerializer,
    UserUploadPartsSerializer,
    UserUploadPresignedURLsSerializer,
    UserUploadSerializer,
)


class UserUploadViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = UserUpload.objects.all()
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ObjectPermissionsFilter,)

    def get_serializer_class(self):
        if self.serializer_class is None:
            if self.action == "create":
                return UserUploadCreateSerializer
            else:
                return UserUploadSerializer
        else:
            return self.serializer_class

    @action(
        detail=True,
        methods=["get"],
        serializer_class=UserUploadPartsSerializer,
    )
    def list_parts(self, request, pk):
        object = self.get_object()
        serializer = self.get_serializer(instance=object)
        return Response(data=serializer.data)

    @action(
        detail=True,
        methods=["patch"],
        serializer_class=UserUploadPresignedURLsSerializer,
    )
    def generate_presigned_urls(self, request, pk):
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
        detail=True,
        methods=["patch"],
        serializer_class=UserUploadCompleteSerializer,
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

    @action(
        detail=True, methods=["patch"],
    )
    def abort_multipart_upload(self, request, pk):
        object = self.get_object()
        object.abort_multipart_upload()
        object.save()

        serializer = self.get_serializer(instance=object)
        return Response(serializer.data)
