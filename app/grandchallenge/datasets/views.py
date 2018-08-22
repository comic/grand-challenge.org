# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.views.generic import ListView, CreateView, DetailView, UpdateView

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.datasets.forms import (
    ImageSetCreateForm,
    ImageSetUpdateForm,
)
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
            "datasets:imageset-update",
            kwargs={
                "challenge_short_name": self.object.challenge.short_name,
                "pk": self.object.pk,
            },
        )


class ImageSetUpdate(UserIsStaffMixin, UpdateView):
    model = ImageSet
    form_class = ImageSetUpdateForm
    template_name_suffix = "_update"


class ImageSetDetail(UserIsStaffMixin, DetailView):
    model = ImageSet
