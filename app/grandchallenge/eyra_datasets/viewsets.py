from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet

from grandchallenge.eyra_datasets.models import EyraDataSet, EyraDataSetFile
from grandchallenge.eyra_datasets.serializers import EyraDataSetSerializer, EyraDataSetFileSerializer


class EyraDataSetAccessPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        elif request.method in ["POST", "PATCH", "PUT"]:
            return request.user and request.user.is_authenticated
        return False

    def has_object_permission(self, request, view, dataset):
        if request.method in ["PUT", "PATCH"]:
            return dataset.creator == request.user
        return True


class EyraDataSetViewSet(ModelViewSet):
    queryset = EyraDataSet.objects.all()
    serializer_class = EyraDataSetSerializer
    permission_classes = (EyraDataSetAccessPermission,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        if self.action == "list":
            return EyraDataSet.objects.filter(frozen=True)
        return EyraDataSet.objects.all()



class EyraDataSetFileViewSet(ModelViewSet):
    queryset = EyraDataSetFile.objects.all()
    serializer_class = EyraDataSetFileSerializer
    permission_classes = (EyraDataSetAccessPermission,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        if self.action == "list":
            return EyraDataSet.objects.filter(frozen=True)
        return EyraDataSet.objects.all()
