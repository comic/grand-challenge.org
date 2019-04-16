from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from grandchallenge.worklists.models import Worklist
from grandchallenge.worklists.serializers import WorklistSerializer


class WorklistViewSet(viewsets.ModelViewSet):
    serializer_class = WorklistSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        title = data.get("title")
        images = data.get("image", "")

        if title is None or len(data["title"]) == 0:
            return Response(
                "Title field is not set.", status=status.HTTP_400_BAD_REQUEST
            )

        if "user" in data and len(data["user"]) > 0:
            user = User.objects.get(pk=data["user"])

        worklist = Worklist.objects.create(
            title=title, user=user, images=images
        )
        serialized = WorklistSerializer(worklist)
        return Response(serialized.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = Worklist.objects.filter(
            Q(user=self.request.user.pk) | Q(user=None)
        )
        return queryset
