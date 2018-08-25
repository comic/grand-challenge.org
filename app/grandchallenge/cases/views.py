# -*- coding: utf-8 -*-
from django.views.generic import CreateView, DetailView
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import (
    RawImageFile,
    RawImageUploadSession,
    UPLOAD_SESSION_STATE,
    Image,
)
from grandchallenge.cases.serializers import ImageSerializer
from grandchallenge.core.permissions.mixins import UserIsStaffMixin


class UploadRawFiles(UserIsStaffMixin, CreateView):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        redirect = super().form_valid(form)

        return redirect


class ShowUploadSessionState(UserIsStaffMixin, DetailView):
    model = RawImageUploadSession

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        result["upload_session"] = result["object"]
        result["raw_files"] = RawImageFile.objects.filter(
            upload_session=result["object"]
        ).all()
        result["images"] = Image.objects.filter(origin=result["object"]).all()
        result["process_finished"] = (
            result["object"].session_state == UPLOAD_SESSION_STATE.stopped
        )
        return result


class ViewImage(UserIsStaffMixin, DetailView):
    model = Image
    template_name = "cases/view_image.html"


class ImageViewSet(ReadOnlyModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
