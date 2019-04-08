from django.contrib.auth.models import User
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics, status
from rest_framework.response import Response
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.models import Worklist, WorklistSet
from grandchallenge.worklists.serializers import (
    WorklistSerializer,
    WorklistSetSerializer,
)
from grandchallenge.worklists.forms import (
    WorklistCreateForm,
    WorklistUpdateForm,
    WorklistSetCreateForm,
    WorklistSetUpdateForm,
)

""" Worklist API Endpoints """


class WorklistTable(generics.ListCreateAPIView):
    serializer_class = WorklistSerializer

    def get_queryset(self):
        queryset = get_objects_for_user(
            self.request.user, "worklists.view_worklist"
        )
        return queryset


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        instance = Worklist.objects.get(pk=kwargs["pk"])

        # If there's no instance, continue with standard execution
        try:
            if not user.has_perm("view_worklist", instance):
                return Response(status=status.HTTP_403_FORBIDDEN)

        except Worklist.DoesNotExist:
            pass

        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        instance = Worklist.objects.get(pk=kwargs["pk"])

        # If there's no instance, continue with standard execution
        try:
            if not user.has_perm("delete_worklist", instance):
                return Response(status=status.HTTP_403_FORBIDDEN)

        except Worklist.DoesNotExist:
            pass

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = Worklist.objects.get(pk=kwargs["pk"])

        # If there's no instance, continue with standard execution
        try:
            if not user.has_perm("delete_worklist", instance):
                return Response(status=status.HTTP_403_FORBIDDEN)

        except Worklist.DoesNotExist:
            pass

        return super().destroy(request, *args, **kwargs)


""" WorklistSet API Endpoints """


class WorklistSetTable(generics.ListCreateAPIView):
    serializer_class = WorklistSetSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user

        if "title" not in data or len(data["title"]) == 0:
            return Response(
                "Title field is not set.", status=status.HTTP_400_BAD_REQUEST
            )

        if "user" in data and len(data["user"]) > 0:
            user = User.objects.get(pk=data["user"])

        set = WorklistSet.objects.create(title=data["title"], user=user)
        serialized = WorklistSetSerializer(set)
        return Response(serialized.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = get_objects_for_user(
            self.request.user, "worklists.view_worklistset"
        )
        return queryset


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        instance = WorklistSet.objects.get(pk=kwargs["pk"])

        # If there's no instance, continue with standard execution
        try:
            if not user.has_perm("view_worklistset", instance):
                return Response(status=status.HTTP_403_FORBIDDEN)

        except WorklistSet.DoesNotExist:
            pass

        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        instance = WorklistSet.objects.get(pk=kwargs["pk"])

        # If there's no instance, continue with standard execution
        try:
            if not user.has_perm("delete_worklistset", instance):
                return Response(status=status.HTTP_403_FORBIDDEN)

        except WorklistSet.DoesNotExist:
            pass

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = WorklistSet.objects.get(pk=kwargs["pk"])

        # If there's no instance, continue with standard execution
        try:
            if not user.has_perm("delete_worklistset", instance):
                return Response(status=status.HTTP_403_FORBIDDEN)

        except WorklistSet.DoesNotExist:
            pass

        return super().destroy(request, *args, **kwargs)


""" Worklist Forms Views """


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistCreateForm

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistRemoveView(UserIsStaffMixin, DeleteView):
    model = Worklist
    template_name = "worklists/worklist_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistUpdateForm

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistDisplayView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100
    template_name = "worklists/worklist_display_form.html"


""" WorklistSet Forms Views """


class WorklistSetCreateView(UserIsStaffMixin, CreateView):
    model = WorklistSet
    form_class = WorklistSetCreateForm
    template_name = "worklists/worklistset_form.html"

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetRemoveView(UserIsStaffMixin, DeleteView):
    model = WorklistSet
    template_name = "worklists/worklistset_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetUpdateView(UserIsStaffMixin, UpdateView):
    model = WorklistSet
    form_class = WorklistSetUpdateForm

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetDisplayView(UserIsStaffMixin, ListView):
    model = WorklistSet
    paginate_by = 100
    template_name = "worklists/worklistset_display_form.html"
