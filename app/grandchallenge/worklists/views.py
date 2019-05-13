from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import viewsets, status
from rest_framework.response import Response

from grandchallenge.cases.models import Image
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.subdomains.utils import reverse
from grandchallenge.worklists.forms import WorklistForm
from grandchallenge.worklists.models import Worklist
from grandchallenge.worklists.serializers import WorklistSerializer


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistForm

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistDetailView(UserIsStaffMixin, DetailView):
    model = Worklist
    form_class = WorklistForm


class WorklistDeleteView(UserIsStaffMixin, DeleteView):
    model = Worklist

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistForm

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistListView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100


class WorklistViewSet(viewsets.ModelViewSet):
    serializer_class = WorklistSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        title = data.get("title")
        images = data.get("images", "")

        if "user" in data and len(data["user"]) > 0:
            try:
                user = User.objects.get(pk=data["user"])
            except ValueError:
                user = None
            except User.DoesNotExist as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

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
            Q(user=self.request.user.pk) | Q(user__isnull=True)
        )
        return queryset
