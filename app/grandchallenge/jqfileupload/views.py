from datetime import timedelta
from uuid import uuid4

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
        kwargs.update(
            {
                "many": True,
                "data": [
                    {
                        "client_id": self.request.POST.get("X-Upload-ID"),
                        "csrf": self.request.META.get("CSRF_COOKIE"),
                        "end_byte": uploaded_file.size - 1,
                        "file": uploaded_file,
                        "filename": uploaded_file.name,
                        "start_byte": 0,
                        "timeout": now() + timedelta(hours=2),
                        "total_size": uploaded_file.size,
                        "upload_path_sha256": generate_upload_path_hash(
                            self.request
                        ),
                        "uuid": uuid4(),
                    }
                    for uploaded_file in self.request.FILES.values()
                ],
            }
        )
        return super().get_serializer(*args, **kwargs)
