# -*- coding: utf-8 -*-
from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.datasets.models import ImageSet


class ImageSetList(UserIsStaffMixin, ListView):
    model = ImageSet


class ImageSetCreate(UserIsStaffMixin, CreateView):
    model = ImageSet


class ImageSetDetail(UserIsStaffMixin, DetailView):
    model = ImageSet
