from django.http import HttpResponse
from rest_framework.decorators import list_route, detail_route
from rest_framework.views import APIView
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

    @detail_route()
    def download(self, request, *args, **kwargs):
        data_file = DataFile.objects.get(pk=kwargs['pk'])
        response = HttpResponse()
        response["Content-Disposition"] = "attachment; filename={0}".format(data_file.name)
        response['X-Accel-Redirect'] = '/download/' + str(data_file.file.url)
        return response


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
