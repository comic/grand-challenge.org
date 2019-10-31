from rest_framework import status, viewsets
from rest_framework.response import Response

from grandchallenge.cases.models import Image
from grandchallenge.worklists.models import Worklist
from grandchallenge.worklists.serializers import WorklistSerializer


class WorklistViewSet(viewsets.ModelViewSet):
    serializer_class = WorklistSerializer

    def create(self, request, *args, **kwargs):
        creator = request.user
        title = request.data.get("title", "")
        image_pks = request.data.get("images", "")

        worklist = Worklist.objects.create(title=title, creator=creator)
        image_set = Image.objects.filter(pk__in=image_pks)
        for image in image_set:
            worklist.images.add(image)
        worklist.save()

        serialized = WorklistSerializer(worklist)
        return Response(serialized.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = Worklist.objects.filter(creator=self.request.user.pk)
        return queryset
