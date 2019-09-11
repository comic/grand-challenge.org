import re
from datetime import timedelta
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated, AllowAny
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

    def perform_create(self, serializer):
        serializer.save(csrf=self.csrf)

    @property
    def csrf(self):
        return self.request.META.get("CSRF_COOKIE")

    def _handle_complete(self, uploaded_file):
        return {
            "client_id": None,
            "end_byte": uploaded_file.size - 1,
            "file": uploaded_file,
            "filename": uploaded_file.name,
            "start_byte": 0,
            "timeout": now() + timedelta(hours=2),
            "total_size": uploaded_file.size,
            "upload_path_sha256": generate_upload_path_hash(self.request),
            "uuid": uuid4(),
        }

    def _handle_chunked(self, uploaded_file):
        # Only content ranges of the form
        #
        #   bytes-unit SP byte-range-resp
        #
        # according to rfc7233 are accepted. See here:
        # https://tools.ietf.org/html/rfc7233#appendix-C
        range_header = self.request.META.get("HTTP_CONTENT_RANGE")

        if not range_header:
            raise ValidationError("Client did not supply Content-Range")

        range_match = re.match(
            r"bytes (?P<start>[0-9]{1,32})-(?P<end>[0-9]{1,32})/(?P<length>\*|[0-9]{1,32})",
            range_header,
        )
        if not range_match:
            raise ValidationError("Supplied invalid Content-Range")

        start_byte = int(range_match.group("start"))
        end_byte = int(range_match.group("end"))
        if (range_match.group("length") is None) or (
            range_match.group("length") == "*"
        ):
            total_size = None
        else:
            total_size = int(range_match.group("length"))

        client_id = self.request.META.get(
            "X-Upload-ID", self.request.POST.get("X-Upload-ID", None)
        )
        if not client_id:
            raise ValidationError("Client did not supply a X-Upload-ID")

        # Verify consistency and generate file ids
        other_chunks = StagedFile.objects.filter(
            csrf=self.csrf,
            client_id=client_id,
            upload_path_sha256=generate_upload_path_hash(self.request),
        ).all()
        if len(other_chunks) == 0:
            file_id = uuid4()
        else:
            chunk_intersects = other_chunks.filter(
                start_byte__lte=end_byte, end_byte__gte=start_byte
            ).exists()
            if chunk_intersects:
                raise ValidationError("Overlapping chunks")

            inconsistent_filenames = other_chunks.exclude(
                client_filename=uploaded_file.name
            ).exists()
            if inconsistent_filenames:
                raise ValidationError("Chunks have inconsistent filenames")

            if total_size is not None:
                inconsistent_total_size = (
                    other_chunks.exclude(total_size=None)
                    .exclude(total_size=total_size)
                    .exists()
                )
                if inconsistent_total_size:
                    raise ValidationError("Inconsistent total size")

            file_id = other_chunks[0].file_id

        return {
            "client_id": client_id,
            "end_byte": end_byte,
            "file": uploaded_file,
            "filename": uploaded_file.name,
            "start_byte": start_byte,
            "timeout": now() + timedelta(hours=2),
            "total_size": total_size,
            "upload_path_sha256": generate_upload_path_hash(self.request),
            "uuid": file_id,
        }
