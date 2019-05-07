from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from grandchallenge.cases.models import Image
from grandchallenge.worklists.models import Worklist
from grandchallenge.worklists.serializers import WorklistSerializer


class WorklistViewSet(viewsets.ModelViewSet):
    serializer_class = WorklistSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        title = data.get("title")
        images = data.get("images", "")

        if "user" in data and len(data["user"]) > 0:
            user = User.objects.get(pk=data["user"])

        # Creates worklist, then iterates over the list to add the image relations
        try:
            worklist = Worklist.objects.create(title=title, user=user)
            if images:
                for image in images.split():
                    worklist.images.add(Image.objects.get(pk=image))
            worklist.save()

            serialized = WorklistSerializer(worklist)
            return Response(serialized.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                serialized.data, status=status.HTTP_400_BAD_REQUEST
            )

    def get_queryset(self):
        queryset = Worklist.objects.filter(
            Q(user=self.request.user.pk) | Q(user=None)
        )
        return queryset
