import logging

from django.http import Http404
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

logger = logging.getLogger(__name__)


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
        url_path="(?P<s3_upload_id>[^/]+)/list-parts",
    )
    def list_parts(self, request, pk, s3_upload_id):
        object = self.get_object()

        if object.s3_upload_id != s3_upload_id:
            logger.warning(
                f"Upload ID did not match: {object=}, {s3_upload_id=}"
            )
            raise Http404

        serializer = self.get_serializer(instance=object)
        return Response(data=serializer.data)

    @action(
        detail=True,
        methods=["patch"],
        serializer_class=UserUploadPresignedURLsSerializer,
        url_path="(?P<s3_upload_id>[^/]+)/generate-presigned-urls",
    )
    def generate_presigned_urls(self, request, pk, s3_upload_id):
        object = self.get_object()

        if object.s3_upload_id != s3_upload_id:
            logger.warning(
                f"Upload ID did not match: {object=}, {s3_upload_id=}"
            )
            raise Http404

        if not object.can_upload_more:
            self.permission_denied(request, message="Upload limit reached")

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
        url_path="(?P<s3_upload_id>[^/]+)/complete-multipart-upload",
    )
    def complete_multipart_upload(self, request, pk, s3_upload_id):
        object = self.get_object()

        if object.s3_upload_id != s3_upload_id:
            logger.warning(
                f"Upload ID did not match: {object=}, {s3_upload_id=}"
            )
            raise Http404

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
        detail=True,
        methods=["patch"],
        url_path="(?P<s3_upload_id>[^/]+)/abort-multipart-upload",
    )
    def abort_multipart_upload(self, request, pk, s3_upload_id):
        object = self.get_object()

        if object.s3_upload_id != s3_upload_id:
            logger.warning(
                f"Upload ID did not match: {object=}, {s3_upload_id=}"
            )
            raise Http404

        object.abort_multipart_upload()
        object.save()

        serializer = self.get_serializer(instance=object)
        return Response(serializer.data)
