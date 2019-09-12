from django.http import HttpResponseRedirect
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from comic.eyra_data.models import DataFile, DataType, DataSet
from comic.eyra_data.serializers import DataFileSerializer, DataTypeSerializer, DataSetSerializer
from comic.eyra_users.permissions import EyraPermissions


class DataFileViewSet(ModelViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        if self.action == "list":
            # return DataSet.objects.filter(frozen=True)
            return DataFile.objects.all()
        return DataFile.objects.all()

    @action(detail=True)
    def download(self, request, *args, **kwargs):
        data_file = DataFile.objects.get(pk=kwargs['pk'])
        return HttpResponseRedirect(data_file.get_download_url())


class DataTypeViewSet(ModelViewSet):
    queryset = DataType.objects.all()
    serializer_class = DataTypeSerializer
    permission_classes = (EyraPermissions,)


class DataSetViewSet(ModelViewSet):
    queryset = DataSet.objects.all()
    serializer_class = DataSetSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
