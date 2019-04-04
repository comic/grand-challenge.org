from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ModelViewSet

from grandchallenge.eyra_data.models import DataFile, DataType
from grandchallenge.eyra_data.serializers import DataFileSerializer, DataTypeSerializer


# uses per ObjectPermissions (guardian), but with anonymous read-only.
class AnonDjangoObjectPermissions(DjangoObjectPermissions):
    authenticated_users_only = False


class DataFileViewSet(ModelViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (AnonDjangoObjectPermissions,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        if self.action == "list":
            # return DataSet.objects.filter(frozen=True)
            return DataFile.objects.all()
        return DataFile.objects.all()


class DataTypeViewSet(ModelViewSet):
    queryset = DataType.objects.all()
    serializer_class = DataTypeSerializer
    permission_classes = (AnonDjangoObjectPermissions,)
