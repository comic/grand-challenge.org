# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.datasets.forms import ImageSetCreateForm
from grandchallenge.datasets.models import ImageSet


class ImageSetList(UserIsStaffMixin, ListView):
    model = ImageSet


class ImageSetCreate(UserIsStaffMixin, CreateView):
    model = ImageSet
    form_class = ImageSetCreateForm
    template_name_suffix = "_create"

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        try:
            return super().form_valid(form)
        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_success_url(self):
        return reverse(
            "datasets:imageset-add-images",
            kwargs={
                "challenge_short_name": self.object.challenge.short_name,
                "pk": self.object.pk,
            },
        )


class AddImagesToImageSet(UserIsStaffMixin, CreateView):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "datasets/imageset_add_images.html"

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.imageset = ImageSet.objects.get(pk=self.kwargs["pk"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "datasets:imageset-detail",
            kwargs={
                "challenge_short_name": self.kwargs["challenge_short_name"],
                "pk": self.kwargs["pk"],
            },
        )


class ImageSetDetail(UserIsStaffMixin, DetailView):
    model = ImageSet
