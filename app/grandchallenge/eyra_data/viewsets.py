import hashlib

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from grandchallenge.eyra_data.models import DataFile, DataType
from grandchallenge.eyra_data.serializers import DataSetSerializer, DataTypeSerializer


class DataSetAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        elif request.method in ["POST", "PATCH", "PUT"]:
            return request.user and request.user.is_authenticated
        return False

    def has_object_permission(self, request, view, obj):
        if request.method in ["PUT", "PATCH"]:
            return obj.creator == request.user
        return True


class DataFileViewSet(ModelViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataSetSerializer
    permission_classes = (DataSetAccessPermission,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        if self.action == "list":
            # return DataSet.objects.filter(frozen=True)
            return DataFile.objects.all()
        return DataFile.objects.all()


class DataTypeViewSet(ReadOnlyModelViewSet):
    queryset = DataType.objects.all()
    serializer_class = DataTypeSerializer
    permission_classes = (permissions.AllowAny,)

#
# @api_view(['PATCH'])
# @permission_classes((permissions.IsAuthenticated,))
# def upload_file(request, uuid):
#     dataset_file = DataSetFile.objects.get(id=uuid)
#     if dataset_file.dataset.creator != request.user:
#         raise PermissionDenied('You do not seem to be the owner of the dataset this file belongs to')
#     dataset_file.file = request.data.get('file')
#     dataset_file.original_file_name = dataset_file.file.name
#     dataset_file.sha = hashlib.sha1(dataset_file.file.open().read()).hexdigest()
#     dataset_file.save()
#     return Response(DataSetFileSerializer(dataset_file).data)
# #
#
# class DataSetFileViewSet(ModelViewSet):
#     queryset = DataSetFile.objects.all()
#     serializer_class = DataSetFileSerializer
#     permission_classes = (permissions.IsAuthenticated,)
