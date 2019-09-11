import re
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet

from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.serializers import StagedFileSerializer
from grandchallenge.jqfileupload.widgets.uploader import (
    generate_upload_path_hash,
)


class StagedFileViewSet(ModelViewSet):
    serializer_class = StagedFileSerializer
    queryset = StagedFile.objects.all()
    permission_classes = [AllowAny]  # TODO: Should be IsAuthenticated

    def create(self, request, *args, **kwargs):
        if "HTTP_CONTENT_RANGE" in self.request.META:
            if not self.range_header or not self.range_match:
                return Response(
                    {"status": "Client did not supply valid Content-Range"},
                    status=HTTP_400_BAD_REQUEST,
                )

        return super().create(request, *args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        if "HTTP_CONTENT_RANGE" in self.request.META:
            handler = self._handle_chunked
        else:
            handler = self._handle_complete

        kwargs.update(
            {
                "many": True,
                "data": [
                    handler(uploaded_file)
                    for uploaded_file in self.request.FILES.values()
                ],
            }
        )
        return super().get_serializer(*args, **kwargs)

    @property
    def csrf(self):
        return self.request.META.get("CSRF_COOKIE")

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

    def _handle_complete(self, uploaded_file):
        return {
            "client_id": self.client_id,
            "csrf": self.csrf,
            "end_byte": uploaded_file.size - 1,
            "file": uploaded_file,
            "filename": uploaded_file.name,
            "start_byte": 0,
            "timeout": now() + timedelta(hours=2),
            "total_size": uploaded_file.size,
            "upload_path_sha256": generate_upload_path_hash(self.request),
        }

    def _handle_chunked(self, uploaded_file):
        # Only content ranges of the form
        #
        #   bytes-unit SP byte-range-resp
        #
        # according to rfc7233 are accepted. See here:
        # https://tools.ietf.org/html/rfc7233#appendix-C
        start_byte = int(self.range_match.group("start"))
        end_byte = int(self.range_match.group("end"))
        if (self.range_match.group("length") is None) or (
            self.range_match.group("length") == "*"
        ):
            total_size = None
        else:
            total_size = int(self.range_match.group("length"))

        return {
            "client_id": self.client_id,
            "csrf": self.csrf,
            "end_byte": end_byte,
            "file": uploaded_file,
            "filename": uploaded_file.name,
            "start_byte": start_byte,
            "timeout": now() + timedelta(hours=2),
            "total_size": total_size,
            "upload_path_sha256": generate_upload_path_hash(self.request),
        }
