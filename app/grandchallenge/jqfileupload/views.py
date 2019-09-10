from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.serializers import StagedFileSerializer


class StagedFileViewSet(ModelViewSet):
    serializer_class = StagedFileSerializer
    queryset = StagedFile.objects.all()
    permission_classes = [AllowAny]  # TODO: Should be IsAuthenticated

    def get_serializer(self, *args, **kwargs):
        kwargs.update({"many": True})
        return super().get_serializer(*args, **kwargs)
