import re
from datetime import timedelta

from django.utils.timezone import now
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyPermissions,
)
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.serializers import StagedFileSerializer


class StagedFileViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = StagedFileSerializer
    queryset = StagedFile.objects.all()
    parser_classes = (FormParser, MultiPartParser)
    permission_classes = (DjangoObjectOnlyPermissions,)
    filter_backends = (ObjectPermissionsFilter,)

    def create(self, request, *args, **kwargs):
        if "HTTP_CONTENT_RANGE" in self.request.META:
            if not self.range_header or not self.range_match:
                return Response(
                    {"status": "Client did not supply valid Content-Range"},
                    status=HTTP_400_BAD_REQUEST,
                )
        return super().create(request, *args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        data = [
            self._handle_file(uploaded_file)
            for uploaded_file in self.request.FILES.values()
        ]

        if data:
            kwargs.update({"many": True, "data": data})

        return super().get_serializer(*args, **kwargs)

    @property
    def user_pk_str(self):
        return str(self.request.user.pk)

    @property
    def client_id(self):
        return self.request.POST.get("X-Upload-ID")

    @property
    def range_header(self):
        return self.request.META.get("HTTP_CONTENT_RANGE")

    @property
    def range_match(self):
        return re.match(
            r"bytes (?P<start>[0-9]{1,32})-(?P<end>[0-9]{1,32})/(?P<length>\*|[0-9]{1,32})",
            self.range_header,
        )

    def _handle_file(self, uploaded_file):
        if "HTTP_CONTENT_RANGE" in self.request.META:
            start_byte = int(self.range_match.group("start"))
            end_byte = int(self.range_match.group("end"))
            if (self.range_match.group("length") is None) or (
                self.range_match.group("length") == "*"
            ):
                total_size = None
            else:
                total_size = int(self.range_match.group("length"))
        else:
            start_byte = 0
            end_byte = uploaded_file.size - 1
            total_size = uploaded_file.size

        return {
            "client_id": self.client_id,
            "end_byte": end_byte,
            "file": uploaded_file,
            "filename": uploaded_file.name,
            "start_byte": start_byte if start_byte is not None else 0,
            "timeout": now() + timedelta(hours=6),
            "total_size": total_size,
            "user_pk_str": self.user_pk_str,
        }

    def _find_last_end_byte(self, files):
        last_end_byte = -1
        for file in files:
            if file["start_byte"] != last_end_byte + 1:
                return last_end_byte
            last_end_byte = file["end_byte"]
        return last_end_byte

    @action(detail=False, methods=["get"])
    def get_current_file_size(self, request):
        client_id = request.GET.get("file", None)
        files = (
            StagedFile.objects.filter(client_id=client_id)
            .order_by("start_byte")
            .values("start_byte", "end_byte")
        )
        return Response({"current_size": self._find_last_end_byte(files)})
